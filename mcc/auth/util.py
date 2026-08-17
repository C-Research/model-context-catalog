from typing import Optional

from mcc.auth.backend import get_user_context
from mcc.auth.db import get_user_by_email, get_user_by_username
from mcc.auth.models import UserModel
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


def can_access(user: Optional[UserModel], tool: ToolModel) -> bool:
    """returns true if user can access tool"""
    if not tool.groups or "public" in tool.groups:
        logger.debug("access granted to %s: public tool", tool.key)
        return True
    if user is None:
        logger.debug("access denied to %s: unauthenticated", tool.key)
        return False
    if "admin" in user.groups:
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


async def get_current_user() -> Optional[UserModel]:
    """resolves auth identity to a UserModel; prefers email, falls back to login"""

    try:
        token = await get_user_context()
    except Exception as exc:
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
                return user
        if login := claims.get("login"):
            if user := await get_user_by_username(login):
                logger.debug("resolved user by login: %s", user.username)
                return user
    except Exception as e:
        logger.warning(
            "User store unavailable, treating request as unauthenticated: %s", e
        )
    return None
