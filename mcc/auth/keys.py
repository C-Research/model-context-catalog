import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from elasticsearch import NotFoundError

from mcc.db import KeysIndex
from mcc.settings import logger

_PREFIX_BYTES = 6
_SECRET_BYTES = 24


def generate_key() -> tuple[str, str]:
    """Mint a new raw key in the form ``mcc_<prefix>_<secret>``.

    The literal ``mcc_`` lets secret scanners flag leaked keys; the prefix is
    the indexed lookup handle; the secret carries the entropy. Returns the
    ``(raw_key, prefix)`` pair — the raw key is never stored.
    """
    prefix = secrets.token_hex(_PREFIX_BYTES)
    secret = secrets.token_urlsafe(_SECRET_BYTES)
    return f"mcc_{prefix}_{secret}", prefix


def hash_key(raw_key: str) -> str:
    """SHA-256 hash of the raw key, hex-encoded."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def parse_prefix(raw_key: str) -> str | None:
    """Extract the prefix segment from a raw key, or None if malformed.

    The secret segment (``token_urlsafe``) may itself contain underscores, so
    we split on only the first two: ``mcc`` / ``<prefix>`` / ``<secret>``.
    """
    parts = raw_key.split("_", 2)
    if len(parts) != 3 or parts[0] != "mcc" or not parts[1] or not parts[2]:
        return None
    return parts[1]


def verify_hash(raw_key: str, stored_hash: str) -> bool:
    """Constant-time comparison of a raw key against a stored hash."""
    return hmac.compare_digest(hash_key(raw_key), stored_hash)


async def verify_api_key(raw_key: str) -> dict | None:
    """Resolve `raw_key` to its record in KeysIndex, or None if invalid/expired.

    Prefix lookup, constant-time hash comparison, and expiry check — shared by
    ApiKeyVerifier (MCP transport auth) and any HTTP route that authenticates
    via API key directly against the keys index, so both paths reject
    malformed/unknown/revoked/expired keys identically.
    """
    prefix = parse_prefix(raw_key)
    if prefix is None:
        return None
    record = await get_key_by_prefix(prefix)
    if record is None:
        return None
    if not verify_hash(raw_key, record["hash"]):
        return None
    raw_expiry = record.get("expires_at")
    expires_at = datetime.fromisoformat(raw_expiry) if raw_expiry else None
    if expires_at is not None and expires_at <= datetime.now(UTC):
        logger.debug("rejecting expired key for %s", record["username"])
        return None
    return record


async def create_key(username: str, ttl_days: int | None) -> str:
    """Mint a key for ``username``, replacing any existing one.

    Computes ``created_at``/``expires_at``, ensures the keys index exists with
    its explicit mapping, then writes the record keyed by username. Returns the
    raw key exactly once — it cannot be recovered afterward. A ``ttl_days`` of
    ``None`` mints a key that never expires (``expires_at`` is null).
    """
    raw_key, prefix = generate_key()
    now = datetime.now(UTC)
    expires_at = now + timedelta(days=ttl_days) if ttl_days is not None else None
    async with KeysIndex() as idx:
        await idx.create()
        await idx.put(
            username,
            {
                "prefix": prefix,
                "hash": hash_key(raw_key),
                "username": username,
                "created_at": now.isoformat(),
                "expires_at": expires_at.isoformat() if expires_at else None,
            },
        )
    return raw_key


async def get_key_by_prefix(prefix: str) -> dict | None:
    """Return the key record matching ``prefix``, or None."""
    async with KeysIndex() as idx:
        docs = await idx.search({"term": {"prefix": prefix}})
        return docs[0] if docs else None


async def list_keys() -> list[dict]:
    """Return all key records."""
    async with KeysIndex() as idx:
        await idx.create()
        return await idx.search({"match_all": {}})


async def revoke_key(username: str) -> None:
    """Delete the key record for ``username``. Raises ValueError if none."""
    async with KeysIndex() as idx:
        try:
            await idx.delete(username)
        except NotFoundError:
            raise ValueError(f"No key found for user '{username}'")
