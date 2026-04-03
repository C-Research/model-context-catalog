import hashlib
import os

from tinydb import TinyDB, where

db = TinyDB(os.environ.get("MCC_USERS_DB", "users.db"))
users = db.table("users")


def hash_token(token: str) -> str:
    return "sha256:" + hashlib.sha256(token.encode()).hexdigest()


def generate_token() -> str:
    return os.urandom(32).hex()


def create_user(
    username: str, tools: list[str] = None, groups: list[str] = None
) -> str:
    if users.search(where("username") == username):
        raise ValueError(f"User '{username}' already exists")
    token = generate_token()
    users.insert(
        {
            "username": username,
            "token_hash": hash_token(token),
            "groups": groups or [],
            "tools": tools or [],
        }
    )
    return token


def delete_user(username: str) -> None:
    removed = users.remove(where("username") == username)
    if not removed:
        raise ValueError(f"User '{username}' not found")


def _user_without_hash(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if k != "token_hash"}


def list_users() -> list[dict]:
    return [_user_without_hash(doc) for doc in users.all()]


def get_user_by_token(token: str) -> dict | None:
    results = users.search(where("token_hash") == hash_token(token))
    if not results:
        return None
    return _user_without_hash(results[0])


def get_user_by_name(username: str) -> dict | None:
    results = users.search(where("username") == username)
    if not results:
        return None
    return _user_without_hash(results[0])


def add_group(username: str, group: str) -> None:
    results = users.search(where("username") == username)
    if not results:
        raise ValueError(f"User '{username}' not found")
    groups = results[0]["groups"]
    if group not in groups:
        users.update({"groups": groups + [group]}, where("username") == username)


def remove_group(username: str, group: str) -> None:
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
    results = users.search(where("username") == username)
    if not results:
        raise ValueError(f"User '{username}' not found")
    tools = results[0]["tools"]
    if tool not in tools:
        users.update({"tools": tools + [tool]}, where("username") == username)


def remove_tool(username: str, tool: str) -> None:
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
