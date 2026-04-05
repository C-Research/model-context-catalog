import logging
from typing import Optional

from mcc.auth.models import UserModel
from mcc.models import ToolModel
from mcc.auth.db import get_user_by_email, get_user_by_username

logger = logging.getLogger("mcc.auth")


def can_access(user: Optional[UserModel], tool: ToolModel) -> bool:
    """returns true if user can access tool"""
    if "public" in tool.groups:
        return True
    if user is None:
        return False
    if "admin" in user.groups:
        return True
    if any(g in user.groups for g in tool.groups):
        return True
    if tool.key in user.tools:
        return True
    return False


async def get_current_user() -> Optional[UserModel]:
    """resolves auth identity to a UserModel; prefers email, falls back to login"""
    from mcc.auth.backend import get_user_context

    try:
        token = await get_user_context()
    except Exception:
        return None
    if token is None:
        return None
    if isinstance(token, UserModel):
        return token
    if hasattr(token, "claims"):
        token = token.claims
    try:
        email = token.get("email") or None
        if email:
            user = await get_user_by_email(email)
            if user:
                return user
        login = token.get("login") or None
        if login:
            return await get_user_by_username(login)
    except Exception as e:
        logger.warning(
            "User store unavailable, treating request as unauthenticated: %s", e
        )
    return None


async def list_tools(text: bool = False) -> dict | str:
    """
    Returns a list of tools that the current user is allowed to execute

    If calling from llm you want to set text=True
    """
    from mcc.loader import loader

    user = await get_current_user()
    tools = {}
    for key, tool in loader.items():
        if tool.can_access(user):
            tools[key] = tool
    if not text:
        return tools
    return "\n\n".join([tool.signature for tool in tools.values()])
