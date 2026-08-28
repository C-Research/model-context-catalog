from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from mcc.auth import (
    add_group,
    add_tool,
    can_access,
    create_user,
    delete_user,
    get_current_user,
    get_user_by_email,
    get_user_by_username,
    list_users,
    remove_group,
    remove_tool,
)
from mcc.auth.keys import create_key, parse_prefix
from mcc.context import ANONYMOUS_USER, UserModel
from mcc.db import UsersIndex


@pytest_asyncio.fixture(autouse=True)
async def _fresh_db(users_idx):
    yield


class TestCreateUser:
    async def test_creates_user_with_username(self):
        await create_user("alice")
        user = await get_user_by_username("alice")
        assert user is not None
        assert user.username == "alice"

    async def test_creates_user_with_email(self):
        await create_user("alice", email="alice@example.com")
        user = await get_user_by_username("alice")
        assert user is not None
        assert user.email == "alice@example.com"

    async def test_creates_user_without_email(self):
        await create_user("alice")
        user = await get_user_by_username("alice")
        assert user is not None
        assert user.email is None

    async def test_duplicate_username_raises(self):
        await create_user("alice")
        with pytest.raises(ValueError, match="already exists"):
            await create_user("alice")

    async def test_duplicate_email_raises(self):
        await create_user("alice", email="alice@example.com")
        with pytest.raises(ValueError, match="already exists"):
            await create_user("bob", email="alice@example.com")

    async def test_admin_group(self):
        await create_user("alice", groups=["admin"])
        user = await get_user_by_username("alice")
        assert user is not None
        assert "admin" in user.groups

    async def test_no_token_stored(self):
        await create_user("alice")
        user = await get_user_by_username("alice")
        assert user is not None
        assert not hasattr(user, "token_hash")


class TestDeleteUser:
    async def test_deletes_user(self):
        await create_user("alice")
        await delete_user("alice")
        assert await get_user_by_username("alice") is None

    async def test_not_found_raises(self):
        with pytest.raises(ValueError, match="not found"):
            await delete_user("ghost")


class TestListUsers:
    async def test_user_without_key_has_none(self):
        await create_user("alice")
        [user] = await list_users()
        assert user.key is None

    async def test_user_with_key_has_prefix_and_timestamps_only(self, keys_idx):
        await create_user("alice")
        raw = await create_key("alice", ttl_days=90)
        prefix = raw.split("_")[1]

        [user] = await list_users()
        assert user.key is not None
        assert user.key["prefix"] == f"mcc_{prefix}"
        assert user.key["created_at"] is not None
        assert user.key["expires_at"] is not None
        assert "hash" not in user.key
        assert raw not in str(user.key)

    async def test_key_field_never_persisted_to_users_index(self, keys_idx):
        await create_user("alice")
        await create_key("alice", ttl_days=90)
        await list_users()  # populates .key in-memory only

        async with UsersIndex() as idx:
            doc = await idx.get("alice")
        assert doc is not None
        assert "key" not in doc

    async def test_key_still_absent_from_index_after_group_update(self, keys_idx):
        await create_user("alice")
        await create_key("alice", ttl_days=90)
        await list_users()
        await add_group("alice", "osint")

        async with UsersIndex() as idx:
            doc = await idx.get("alice")
        assert doc is not None
        assert "key" not in doc


class TestGetUserByUsername:
    async def test_found(self):
        await create_user("alice")
        user = await get_user_by_username("alice")
        assert user is not None
        assert user.username == "alice"

    async def test_not_found(self):
        assert await get_user_by_username("ghost") is None


class TestGetUserByEmail:
    async def test_found(self):
        await create_user("alice", email="alice@example.com")
        user = await get_user_by_email("alice@example.com")
        assert user is not None
        assert user.username == "alice"
        assert user.email == "alice@example.com"

    async def test_not_found(self):
        assert await get_user_by_email("ghost@example.com") is None


class TestGroups:
    async def test_add_group(self):
        await create_user("alice")
        await add_group("alice", "ops")
        user = await get_user_by_username("alice")
        assert user is not None
        assert "ops" in user.groups

    async def test_add_group_idempotent(self):
        await create_user("alice")
        await add_group("alice", "ops")
        await add_group("alice", "ops")
        user = await get_user_by_username("alice")
        assert user is not None
        assert user.groups.count("ops") == 1

    async def test_remove_group(self):
        await create_user("alice")
        await add_group("alice", "ops")
        await remove_group("alice", "ops")
        user = await get_user_by_username("alice")
        assert user is not None
        assert "ops" not in user.groups

    async def test_remove_group_not_member(self):
        await create_user("alice")
        with pytest.raises(ValueError, match="not a member"):
            await remove_group("alice", "ops")


class TestTools:
    async def test_add_tool(self):
        await create_user("alice")
        await add_tool("alice", "echo")
        user = await get_user_by_username("alice")
        assert user is not None
        assert "echo" in user.tools

    async def test_add_tool_idempotent(self):
        await create_user("alice")
        await add_tool("alice", "echo")
        await add_tool("alice", "echo")
        user = await get_user_by_username("alice")
        assert user is not None
        assert user.tools.count("echo") == 1

    async def test_remove_tool(self):
        await create_user("alice")
        await add_tool("alice", "echo")
        await remove_tool("alice", "echo")
        user = await get_user_by_username("alice")
        assert user is not None
        assert "echo" not in user.tools

    async def test_remove_tool_not_present(self):
        await create_user("alice")
        with pytest.raises(ValueError, match="does not have tool"):
            await remove_tool("alice", "echo")


@pytest.mark.smoke
class TestCanAccess:
    def _tool(self, name: str = "echo", groups: list[str] | None = None) -> MagicMock:
        tool = MagicMock()
        tool.name = name
        tool.groups = groups or []
        tool.key = ".".join(sorted(tool.groups) + [name])
        return tool

    def test_empty_groups_no_user(self):
        assert can_access(ANONYMOUS_USER, self._tool(groups=[])) is True

    def test_no_user_with_groups(self):
        assert can_access(ANONYMOUS_USER, self._tool(groups=["ops"])) is False

    def test_admin_bypasses(self):
        user = UserModel(username="admin", groups=["admin"])
        assert can_access(user, self._tool(groups=["ops"])) is True

    def test_group_membership(self):
        user = UserModel(username="alice", groups=["ops"])
        assert can_access(user, self._tool(groups=["ops"])) is True
        assert can_access(user, self._tool(groups=["dev"])) is False

    def test_explicit_tool_grant(self):
        user = UserModel(username="alice", tools=["ops.echo"])
        assert can_access(user, self._tool(name="echo", groups=["ops"])) is True

    def test_no_access(self):
        user = UserModel(username="alice")
        assert can_access(user, self._tool(groups=["ops"])) is False

    def test_prefix_group_matches_leading_segment(self):
        user = UserModel(username="alice", groups=["atlas.*"])
        assert can_access(user, self._tool(groups=["atlas", "core"])) is True
        assert can_access(user, self._tool(groups=["atlas"])) is True

    def test_prefix_group_does_not_match_secondary_tag(self):
        # "atlas" is a secondary tag here, not the leading namespace segment,
        # so "atlas.*" must not grant access.
        user = UserModel(username="alice", groups=["atlas.*"])
        assert can_access(user, self._tool(groups=["admin", "atlas"])) is False

    def test_prefix_group_no_overlap(self):
        user = UserModel(username="alice", groups=["atlas.*"])
        assert can_access(user, self._tool(groups=["sandp", "neo4j"])) is False


class TestGetCurrentUser:
    async def test_resolves_via_email(self):
        await create_user("alice", email="alice@example.com")
        mock_token = MagicMock()
        mock_token.claims = {"email": "alice@example.com", "login": "alice"}
        with patch("mcc.auth.util.get_user_context", return_value=mock_token):
            user = await get_current_user()
        assert user is not None
        assert user.username == "alice"

    async def test_falls_back_to_username(self):
        await create_user("alice")
        mock_token = MagicMock()
        mock_token.claims = {"email": None, "login": "alice"}
        with patch("mcc.auth.util.get_user_context", return_value=mock_token):
            user = await get_current_user()
        assert user is not None
        assert user.username == "alice"

    async def test_email_takes_precedence_over_username(self):
        await create_user("alice", email="alice@example.com")
        await create_user("alice-other")
        mock_token = MagicMock()
        mock_token.claims = {"email": "alice@example.com", "login": "alice-other"}
        with patch("mcc.auth.util.get_user_context", return_value=mock_token):
            user = await get_current_user()
        assert user is not None
        assert user.username == "alice"

    async def test_unauthenticated(self):
        with patch("mcc.auth.util.get_user_context", return_value=None):
            user = await get_current_user()
        assert user is None

    async def test_no_matching_record(self):
        mock_token = MagicMock()
        mock_token.claims = {"email": None, "login": "unknown"}
        with patch("mcc.auth.util.get_user_context", return_value=mock_token):
            user = await get_current_user()
        assert user is None


class TestGetCurrentUserKeyPrefix:
    """get_current_user() attaches the resolved user's key prefix by looking
    it up in the keys index directly, regardless of which auth backend
    (email/login claims here) authenticated this particular request — a
    user who normally logs in via OAuth/JWT may still have an API key on
    file for other uses (e.g. CI)."""

    async def test_user_with_a_key_gets_its_prefix(self, keys_idx):
        await create_user("alice")
        raw = await create_key("alice", ttl_days=90)
        mock_token = MagicMock()
        mock_token.claims = {"email": None, "login": "alice"}
        with patch("mcc.auth.util.get_user_context", return_value=mock_token):
            user = await get_current_user()
        assert user is not None
        assert user.key == {"prefix": parse_prefix(raw)}

    async def test_user_without_a_key_has_no_prefix(self):
        await create_user("alice")
        mock_token = MagicMock()
        mock_token.claims = {"email": None, "login": "alice"}
        with patch("mcc.auth.util.get_user_context", return_value=mock_token):
            user = await get_current_user()
        assert user is not None
        assert user.key is None
