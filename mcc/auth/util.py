from mcc.auth.backend import get_user_context
from mcc.auth.db import get_user_by_email, get_user_by_username
from mcc.auth.keys import verify_api_key
from mcc.context import UserModel
from mcc.db import KeysIndex
from mcc.models import ToolModel
from mcc.settings import logger


def _group_matches(pattern: str, groups: list[str]) -> bool:
    """True if `pattern` grants access given a tool's authored groups list.

    A plain tag (e.g. "atlas") matches via exact membership, same as before.
    A pattern ending in ".*" (e.g. "atlas.*") is a prefix match against the
    tool's groups in their declared order (file-level groups first, then any
    per-entry groups) — it only matches tools where "atlas" leads the group
    path, not tools where "atlas" merely appears as a secondary tag.
    """
    if pattern.endswith(".*"):
        prefix = pattern[:-2].split(".")
        return groups[: len(prefix)] == prefix
    return pattern in groups


def can_access(user: UserModel, tool: ToolModel) -> bool:
    """returns true if user can access tool"""
    if not tool.groups or "public" in tool.groups:
        logger.debug("access granted to %s: public tool", tool.key)
        return True
    if user.is_admin:
        logger.debug("access granted to %s: %s is admin", tool.key, user.username)
        return True
    if any(_group_matches(g, tool.groups) for g in user.groups):
        logger.debug(
            "access granted to %s: group overlap for %s", tool.key, user.username
        )
        return True
    if tool.key in user.tools:
        logger.debug(
            "access granted to %s: explicit grant for %s", tool.key, user.username
        )
        return True
    logger.debug(
        "access denied to %s: %s has no matching group or grant",
        tool.key,
        user.username,
    )
    return False


def whoami_info(user: UserModel) -> dict:
    """Assembles a user's identity + accessible-tool-keys summary.

    Shared by the whoami MCP tool (renders as text) and the /whoami HTTP route
    (renders as JSON), so both surfaces report the same fields. Callers handle
    the unauthenticated case themselves before calling this.
    """
    accessible = [t.key for t in user.accessible_tools]
    return {
        "username": user.username,
        "email": user.email,
        "groups": user.groups,
        "tools": accessible,
    }


async def _attach_key_prefix(user: UserModel) -> UserModel:
    """Attaches the resolved user's current API key prefix, if any, regardless
    of which auth backend authenticated this request — a user who normally
    logs in via OAuth/JWT may still have a provisioned API key on file. Keys
    are stored one per user, keyed by username, so this is a direct lookup.
    """
    async with KeysIndex() as idx:
        record = await idx.get(user.username)
    if record:
        user.key = {"prefix": record["prefix"]}
    return user


async def get_current_user() -> UserModel | None:
    """resolves auth identity to a UserModel; prefers email, falls back to login"""

    try:
        token = await get_user_context()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Error getting user context: %s", exc)
        return None
    if token is None:
        logger.warning("No token returned from auth backend")
        return None
    if isinstance(token, UserModel):
        logger.debug("resolved user directly from token: %s", token.username)
        return token
    claims: dict = getattr(token, "claims", {}) or {}
    logger.info("auth token claims: %s", claims)
    try:
        if email := claims.get("email"):
            user = await get_user_by_email(email)
            logger.info("email lookup for %s -> %s", email, user)
            if user:
                logger.debug("resolved user by email: %s", user.username)
                return await _attach_key_prefix(user)
        if (login := claims.get("login")) and (
            user := await get_user_by_username(login)
        ):
            logger.debug("resolved user by login: %s", user.username)
            return await _attach_key_prefix(user)
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "User store unavailable, treating request as unauthenticated: %s", e
        )
    return None


async def get_user_by_key(
    raw_key: str, groups: list[str] | None = None
) -> UserModel | None:
    """Resolves `raw_key` to a UserModel via the keys index directly.

    Independent of `settings.auth`/`get_provider()` — HTTP routes that gate on
    this always check the raw key against the mcc-keys index, so they don't
    inherit whatever OAuth/JWT backend the MCP transport is configured with.

    If `groups` is given, the resolved user must belong to at least one of
    them, unless they're an admin — same admin-bypass semantics as
    `can_access`. If `groups` is None, any successfully resolved user passes.
    Returns None for an invalid/expired/unknown key, an unknown username, or
    a user that doesn't satisfy `groups`.
    """
    record = await verify_api_key(raw_key)
    if record is None:
        return None
    user = await get_user_by_username(record["username"])
    if user is None:
        return None
    if (
        groups is not None
        and not user.is_admin
        and not any(g in user.groups for g in groups)
    ):
        return None
    user.key = {"prefix": record["prefix"]}
    return user
