from typing import Optional

from mcc.auth.backend import get_user_context
from mcc.auth.db import get_user_by_email, get_user_by_username
from mcc.auth.models import UserModel
from mcc.models import ToolModel
from mcc.settings import logger


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
    if any(g in user.groups for g in tool.groups):
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
        return
    if token is None:
        logger.warning("No token returned from auth backend")
        return
    if isinstance(token, UserModel):
        logger.debug("resolved user directly from token: %s", token.username)
        return token
    claims: dict = getattr(token, "claims", {}) or {}
    try:
        email = claims.get("email") or None
        if email:
            user = await get_user_by_email(email)
            if user:
                logger.debug("resolved user by email: %s", user.username)
                return user
        login = claims.get("login") or None
        if login:
            user = await get_user_by_username(login)
            if user:
                logger.debug("resolved user by login: %s", user.username)
            return user
    except Exception as e:
        logger.warning(
            "User store unavailable, treating request as unauthenticated: %s", e
        )
    return


async def list_tools(text: bool = False) -> dict | str:
    """
    Returns a list of tools that the current user is allowed to execute

    If calling from llm you want to set text=True
    """
    from mcc.loader import loader

    user = await get_current_user()
    tools = {}
    for key, tool in loader.items():
        if tool.allows(user):
            tools[key] = tool
    if not text:
        return tools
    return "\n\n".join([tool.signature for tool in tools.values()])
