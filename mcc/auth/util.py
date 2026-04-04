from mcc.models import ToolModel
from mcc.auth.db import get_user_by_email, get_user_by_username


def can_access(user: dict | None, tool: ToolModel) -> bool:
    """returns true if user can access tool (tool must have .name and .groups)"""
    if "public" in tool.groups:
        return True
    if user is None:
        return False
    user_groups = user.get("groups", [])
    if "admin" in user_groups:
        return True
    if any(g in user_groups for g in tool.groups):
        return True
    if tool.key in user.get("tools", []):
        return True
    return False


async def get_current_user() -> dict | None:
    """resolves auth identity to a user dict; prefers email, falls back to login"""
    from mcc.auth.backend import get_user_context

    token = get_user_context()
    if token is None:
        return
    if hasattr(token, "claims"):
        token = token.claims
    email = token.get("email") or None
    if email:
        user = get_user_by_email(email)
        if user:
            return user
    login = token.get("login") or None
    if login:
        return get_user_by_username(login)
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
        if tool.can_access(user):
            tools[key] = tool
    if not text:
        return tools
    return "\n\n".join([tool.signature for tool in tools.values()])
