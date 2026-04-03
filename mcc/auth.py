import os

from fastmcp.server.dependencies import get_access_token
from tinydb import TinyDB, where

db = TinyDB(os.environ.get("MCC_USERS_DB", "users.db"))
users = db.table("users")


def create_user(
    username: str,
    email: str = None,
    tools: list[str] = None,
    groups: list[str] = None,
) -> None:
    """creates a user and assigns their tools/groups perms"""
    if users.search(where("username") == username):
        raise ValueError(f"User '{username}' already exists")
    if email and users.search(where("email") == email):
        raise ValueError(f"Email '{email}' already exists")
    users.insert(
        {
            "username": username,
            "email": email,
            "groups": groups or [],
            "tools": tools or [],
        }
    )


def delete_user(username: str) -> None:
    """deletes a user from the db"""
    removed = users.remove(where("username") == username)
    if not removed:
        raise ValueError(f"User '{username}' not found")


def list_users() -> list[dict]:
    return [dict(doc) for doc in users.all()]


def get_user_by_username(username: str) -> dict | None:
    results = users.search(where("username") == username)
    if not results:
        return None
    return dict(results[0])


def get_user_by_email(email: str) -> dict | None:
    results = users.search(where("email") == email)
    if not results:
        return None
    return dict(results[0])


def add_group(username: str, group: str) -> None:
    """adds a user to a group"""
    results = users.search(where("username") == username)
    if not results:
        raise ValueError(f"User '{username}' not found")
    groups = results[0]["groups"]
    if group not in groups:
        users.update({"groups": groups + [group]}, where("username") == username)


def remove_group(username: str, group: str) -> None:
    """removes a user from a group"""
    results = users.search(where("username") == username)
    if not results:
        raise ValueError(f"User '{username}' not found")
    groups = results[0]["groups"]
    if group not in groups:
        raise ValueError(f"User '{username}' is not a member of group '{group}'")
    users.update(
        {"groups": [g for g in groups if g != group]}, where("username") == username
    )


def add_tool(username: str, tool: str) -> None:
    """adds a tool permission to the user"""
    results = users.search(where("username") == username)
    if not results:
        raise ValueError(f"User '{username}' not found")
    tools = results[0]["tools"]
    if tool not in tools:
        users.update({"tools": tools + [tool]}, where("username") == username)


def remove_tool(username: str, tool: str) -> None:
    """removes a tool permission from the user"""
    results = users.search(where("username") == username)
    if not results:
        raise ValueError(f"User '{username}' not found")
    tools = results[0]["tools"]
    if tool not in tools:
        raise ValueError(f"User '{username}' does not have tool '{tool}'")
    users.update(
        {"tools": [t for t in tools if t != tool]}, where("username") == username
    )


def can_access(user: dict | None, tool_name: str, tool_group: str | None) -> bool:
    """returns true if user can access tool"""
    if tool_group == "public":
        return True
    if user is None:
        return False
    groups = user.get("groups", [])
    if "admin" in groups:
        return True
    if tool_group and tool_group in groups:
        return True
    if tool_name in user.get("tools", []):
        return True
    return False


async def get_current_user(ctx) -> dict | None:
    """resolves GitHub identity to a user dict; prefers email, falls back to login"""
    token = get_access_token()
    if token is None:
        return None
    email = token.claims.get("email") or None
    if email:
        user = get_user_by_email(email)
        if user:
            return user
    login = token.claims.get("login") or None
    if login:
        return get_user_by_username(login)
    return None
