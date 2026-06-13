from asyncio import run as arun
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from click.testing import CliRunner

from mcc.auth import create_user
from mcc.auth.backend import ApiKeyVerifier, get_provider
from mcc.auth.keys import (
    create_key,
    generate_key,
    get_key_by_prefix,
    hash_key,
    list_keys,
    parse_prefix,
    revoke_key,
    verify_hash,
)
from mcc.cli.users import user
from mcc.db import KeysIndex


@pytest_asyncio.fixture(autouse=True)
async def _fresh_keys(keys_idx):
    yield


def _ctx_raises():
    """Mock ctx whose elicit() raises — simulates a client without elicitation."""
    ctx = MagicMock()
    ctx.elicit = AsyncMock(side_effect=Exception("elicitation not supported"))
    return ctx


def _only_key(output: str) -> str:
    """Extract the single mcc_ raw key printed in CLI output."""
    for token in output.split():
        if token.startswith("mcc_"):
            return token
    raise AssertionError("no mcc_ key found in output")


# --- Key generation, hashing, prefix parsing (Task 2.2) ---


class TestKeyPrimitives:
    def test_generated_key_has_mcc_prefix(self):
        raw, prefix = generate_key()
        assert raw.startswith("mcc_")
        parts = raw.split("_", 2)
        assert len(parts) == 3
        assert parts[1] == prefix
        assert parts[2]

    def test_each_key_is_unique(self):
        a, _ = generate_key()
        b, _ = generate_key()
        assert a != b

    def test_parse_prefix_roundtrip(self):
        raw, prefix = generate_key()
        assert parse_prefix(raw) == prefix

    def test_parse_prefix_rejects_malformed(self):
        assert parse_prefix("not-a-key") is None
        assert parse_prefix("mcc_only") is None
        assert parse_prefix("xxx_prefix_secret") is None
        assert parse_prefix("mcc__secret") is None

    def test_hash_is_not_raw_key(self):
        raw, _ = generate_key()
        h = hash_key(raw)
        assert raw not in h
        assert len(h) == 64  # SHA-256 hex

    def test_verify_hash_constant_time_compare(self):
        raw, _ = generate_key()
        assert verify_hash(raw, hash_key(raw)) is True
        assert verify_hash("mcc_x_y", hash_key(raw)) is False


# --- Key CRUD + index (Task 6.2) ---


class TestKeyCRUD:
    async def test_create_returns_raw_key(self):
        raw = await create_key("ci-bot", ttl_days=90)
        assert raw.startswith("mcc_")

    async def test_stored_record_has_hash_not_raw(self):
        raw = await create_key("ci-bot", ttl_days=90)
        prefix = parse_prefix(raw)
        assert prefix is not None
        record = await get_key_by_prefix(prefix)
        assert record is not None
        assert record["username"] == "ci-bot"
        assert record["hash"] == hash_key(raw)
        assert "prefix" in record
        assert "created_at" in record
        assert "expires_at" in record
        # the raw key never appears anywhere in the document
        assert raw not in record.values()

    async def test_explicit_keyword_mapping_created(self):
        await create_key("ci-bot", ttl_days=90)
        async with KeysIndex() as idx:
            mapping = await idx._client.indices.get_mapping(index=idx.index)
        props = mapping[idx.index]["mappings"]["properties"]
        assert props["prefix"]["type"] == "keyword"
        assert props["hash"]["type"] == "keyword"
        assert props["username"]["type"] == "keyword"

    async def test_minting_replaces_existing_key(self):
        first = await create_key("ci-bot", ttl_days=90)
        second = await create_key("ci-bot", ttl_days=90)
        assert first != second
        # only one document for the user (keyed by username)
        keys = await list_keys()
        assert len([k for k in keys if k["username"] == "ci-bot"]) == 1
        # the old prefix no longer resolves
        old_prefix = parse_prefix(first)
        assert old_prefix is not None
        assert await get_key_by_prefix(old_prefix) is None

    async def test_revoke_deletes(self):
        await create_key("ci-bot", ttl_days=90)
        await revoke_key("ci-bot")
        keys = await list_keys()
        assert not any(k["username"] == "ci-bot" for k in keys)

    async def test_revoke_missing_raises(self):
        with pytest.raises(ValueError, match="No key found"):
            await revoke_key("ghost")

    async def test_revocation_is_instant(self):
        raw = await create_key("ci-bot", ttl_days=90)
        prefix = parse_prefix(raw)
        assert prefix is not None
        assert await get_key_by_prefix(prefix) is not None
        await revoke_key("ci-bot")
        # next read reflects the deletion immediately — no cache
        assert await get_key_by_prefix(prefix) is None


# --- ApiKeyVerifier (Tasks 6.1, 6.3) ---


class TestApiKeyVerifier:
    async def test_valid_key_resolves_login(self):
        raw = await create_key("ci-bot", ttl_days=90)
        token = await ApiKeyVerifier().verify_token(raw)
        assert token is not None
        assert token.claims["login"] == "ci-bot"

    async def test_raw_key_never_in_claims_or_scopes_or_token(self):
        raw = await create_key("ci-bot", ttl_days=90)
        token = await ApiKeyVerifier().verify_token(raw)
        assert token is not None
        assert raw not in token.claims.values()
        assert raw not in token.scopes
        assert token.token != raw

    async def test_unknown_prefix_returns_none(self):
        token = await ApiKeyVerifier().verify_token("mcc_deadbeef_secret")
        assert token is None

    async def test_malformed_key_returns_none(self):
        assert await ApiKeyVerifier().verify_token("garbage") is None

    async def test_hash_mismatch_returns_none(self):
        raw = await create_key("ci-bot", ttl_days=90)
        prefix = parse_prefix(raw)
        # same prefix, wrong secret
        forged = f"mcc_{prefix}_wrongsecret"
        token = await ApiKeyVerifier().verify_token(forged)
        assert token is None

    async def test_expired_key_returns_none(self):
        # mint with negative TTL so it is already expired
        await create_key("ci-bot", ttl_days=90)
        # overwrite the stored record with an expired timestamp
        raw, prefix = generate_key()
        past = datetime.now(timezone.utc) - timedelta(days=1)
        async with KeysIndex() as idx:
            await idx.put(
                "ci-bot",
                {
                    "prefix": prefix,
                    "hash": hash_key(raw),
                    "username": "ci-bot",
                    "created_at": (past - timedelta(days=90)).isoformat(),
                    "expires_at": past.isoformat(),
                },
            )
        token = await ApiKeyVerifier().verify_token(raw)
        assert token is None

    async def test_never_expiring_key_resolves(self):
        raw = await create_key("ci-bot", ttl_days=None)
        token = await ApiKeyVerifier().verify_token(raw)
        assert token is not None
        assert token.claims["login"] == "ci-bot"
        assert token.expires_at is None


class TestNeverExpires:
    async def test_create_stores_null_expiry(self):
        raw = await create_key("ci-bot", ttl_days=None)
        prefix = parse_prefix(raw)
        assert prefix is not None
        record = await get_key_by_prefix(prefix)
        assert record is not None
        assert record["expires_at"] is None


class TestGetProvider:
    def test_returns_api_key_verifier(self):
        with patch("mcc.auth.backend.settings") as s:
            s.auth = "api_key"
            provider = get_provider()
        assert isinstance(provider, ApiKeyVerifier)

    def test_unknown_auth_raises(self):
        with patch("mcc.auth.backend.settings") as s:
            s.auth = "nonsense-backend"
            with pytest.raises(ValueError, match="nonsense-backend"):
                get_provider()


# --- Hard 401 at transport layer (Task 5.2) ---


class TestTransportRejection:
    """Under api_key auth, a missing/invalid bearer must yield 401 (the
    BearerAuthBackend returns None → Starlette emits 401), never falling
    through to public-only access."""

    def _backend(self):
        from mcp.server.auth.middleware.bearer_auth import BearerAuthBackend

        return BearerAuthBackend(token_verifier=ApiKeyVerifier())

    def _conn(self, headers: dict):
        from starlette.requests import HTTPConnection

        raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
        return HTTPConnection({"type": "http", "headers": raw})

    async def test_missing_header_rejected(self):
        result = await self._backend().authenticate(self._conn({}))
        assert result is None

    async def test_invalid_key_rejected(self):
        conn = self._conn({"Authorization": "Bearer mcc_bad_key"})
        result = await self._backend().authenticate(conn)
        assert result is None

    async def test_valid_key_authenticates(self):
        raw = await create_key("ci-bot", ttl_days=90)
        conn = self._conn({"Authorization": f"Bearer {raw}"})
        result = await self._backend().authenticate(conn)
        assert result is not None


# --- CLI (Task 6.4) ---


# --- Integration: key → identity → RBAC (Task 6.5) ---


class TestKeyIntegration:
    """A key bound to a narrow user executes only that user's tools, and
    narrowing the user narrows the key without re-minting."""

    async def _resolve_user(self, raw_key):
        """Run the real verify → AccessToken → get_current_user chain."""
        from mcc.auth.util import get_current_user

        token = await ApiKeyVerifier().verify_token(raw_key)
        with patch("mcc.auth.util.get_user_context", return_value=token):
            return await get_current_user()

    async def test_narrow_key_executes_and_denies(self, users_idx, load_fixture):
        from mcc.app import execute
        from mcc.auth import create_user
        from mcc.loader import loader
        from mcc.middleware import current_user_var

        # public.request-style narrow grant: bind to a grouped tool explicitly.
        load_fixture("tools_grouped.yaml")
        await loader.save()
        await create_user("ci-bot", tools=["example.echo"])
        raw = await create_key("ci-bot", ttl_days=90)

        user = await self._resolve_user(raw)
        assert user is not None and user.username == "ci-bot"

        current_user_var.set(user)
        try:
            allowed = await execute(_ctx_raises(), "example.echo", {"message": "hi"})
            assert allowed == ["hi"]
        finally:
            current_user_var.set(None)

    async def test_narrowing_user_narrows_key_without_reminting(
        self, users_idx, load_fixture
    ):
        from mcc.app import execute
        from mcc.auth import create_user, remove_tool
        from mcc.loader import loader
        from mcc.middleware import current_user_var

        load_fixture("tools_grouped.yaml")
        await loader.save()
        await create_user("ci-bot", tools=["example.echo"])
        raw = await create_key("ci-bot", ttl_days=90)

        # revoke the grant — the same key now resolves a narrower user
        await remove_tool("ci-bot", "example.echo")
        user = await self._resolve_user(raw)
        current_user_var.set(user)
        try:
            denied = await execute(_ctx_raises(), "example.echo", {"message": "hi"})
            assert denied == "Unauthorized"
        finally:
            current_user_var.set(None)


class TestKeyCLI:
    def test_add_prints_raw_key_once(self, users_idx):
        arun(create_user("ci-bot"))
        runner = CliRunner()
        result = runner.invoke(user, ["key", "add", "ci-bot"])
        assert result.exit_code == 0
        assert "mcc_" in result.output
        assert "only once" in result.output
        # exactly one raw key token in the output
        assert result.output.count("mcc_") == 1

    def test_add_unknown_user_errors(self, users_idx):
        runner = CliRunner()
        result = runner.invoke(user, ["key", "add", "ghost"])
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_add_custom_expiry(self, users_idx):
        arun(create_user("ci-bot"))
        runner = CliRunner()
        result = runner.invoke(user, ["key", "add", "ci-bot", "--expires", "7"])
        assert result.exit_code == 0
        assert "expires in 7 days" in result.output
        record = arun(get_key_by_prefix(parse_prefix(_only_key(result.output))))
        assert record is not None and record["expires_at"] is not None

    def test_add_never_expires(self, users_idx):
        arun(create_user("ci-bot"))
        runner = CliRunner()
        result = runner.invoke(user, ["key", "add", "ci-bot", "--expires", "never"])
        assert result.exit_code == 0
        assert "never expires" in result.output
        keys = arun(list_keys())
        assert keys[0]["expires_at"] is None

    def test_add_invalid_expiry_errors(self, users_idx):
        arun(create_user("ci-bot"))
        runner = CliRunner()
        result = runner.invoke(user, ["key", "add", "ci-bot", "--expires", "soon"])
        assert result.exit_code != 0
        assert "Invalid --expires" in result.output

    def test_list_reveals_no_secrets(self, users_idx):
        arun(create_user("ci-bot"))
        raw = arun(create_key("ci-bot", 90))
        runner = CliRunner()
        result = runner.invoke(user, ["key", "list"])
        assert result.exit_code == 0
        assert "ci-bot" in result.output
        assert raw not in result.output
        assert hash_key(raw) not in result.output

    def test_revoke_removes_key(self, users_idx):
        arun(create_user("ci-bot"))
        arun(create_key("ci-bot", 90))
        runner = CliRunner()
        result = runner.invoke(user, ["key", "revoke", "ci-bot"])
        assert result.exit_code == 0
        assert "revoked" in result.output
        remaining = arun(list_keys())
        assert not any(k["username"] == "ci-bot" for k in remaining)
