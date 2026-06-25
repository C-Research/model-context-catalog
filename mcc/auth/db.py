from typing import Optional

from elasticsearch import NotFoundError

from mcc.auth.models import UserModel
from mcc.cache import cache
from mcc.db import UsersIndex


async def _invalidate_whoami(username: str) -> None:
    """Drop the cached whoami response for a user after their perms change."""
    await cache.delete(f"whoami:{username}")


async def create_user(
    username: str,
    email: Optional[str] = None,
    tools: Optional[list[str]] = None,
    groups: Optional[list[str]] = None,
) -> None:
    """creates a user and assigns their tools/groups perms"""
    async with UsersIndex() as idx:
        if await idx.get(username):
            raise ValueError(f"User '{username}' already exists")
        if email and await idx.search({"term": {"email": email}}):
            raise ValueError(f"Email '{email}' already exists")
        user = UserModel(
            username=username, email=email, groups=groups or [], tools=tools or []
        )
        await idx.put(username, user.model_dump())
    await _invalidate_whoami(username)


async def delete_user(username: str) -> None:
    """deletes a user from the db"""
    async with UsersIndex() as idx:
        try:
            await idx.delete(username)
        except NotFoundError:
            raise ValueError(f"User '{username}' not found")
    await _invalidate_whoami(username)


async def list_users() -> list[UserModel]:
    async with UsersIndex() as idx:
        docs = await idx.search({"match_all": {}})
        return [UserModel(**doc) for doc in docs]


async def get_user_by_username(username: str) -> Optional[UserModel]:
    async with UsersIndex() as idx:
        doc = await idx.get(username)
        return UserModel(**doc) if doc else None


async def get_user_by_email(email: str) -> Optional[UserModel]:
    async with UsersIndex() as idx:
        docs = await idx.search({"term": {"email": email}})
        return UserModel(**docs[0]) if docs else None


async def _update_user(username: str, user: UserModel) -> None:
    async with UsersIndex() as idx:
        await idx.put(username, user.model_dump())
    await _invalidate_whoami(username)


async def _modify_user_list(
    username: str, field: str, value: str, *, add: bool
) -> None:
    """Add or remove a value from a user's list field ('groups' or 'tools').

    Adds are idempotent (a no-op if already present); removes raise ValueError
    if the value is absent. Persists and invalidates the whoami cache on change.
    """
    user = await get_user_by_username(username)
    if user is None:
        raise ValueError(f"User '{username}' not found")
    current: list[str] = getattr(user, field)
    if add:
        if value in current:
            return
        setattr(user, field, current + [value])
    else:
        if value not in current:
            if field == "groups":
                raise ValueError(
                    f"User '{username}' is not a member of group '{value}'"
                )
            raise ValueError(f"User '{username}' does not have tool '{value}'")
        setattr(user, field, [v for v in current if v != value])
    await _update_user(username, user)


async def add_group(username: str, group: str) -> None:
    """adds a user to a group"""
    await _modify_user_list(username, "groups", group, add=True)


async def remove_group(username: str, group: str) -> None:
    """removes a user from a group"""
    await _modify_user_list(username, "groups", group, add=False)


async def add_tool(username: str, tool: str) -> None:
    """adds a tool permission to the user"""
    await _modify_user_list(username, "tools", tool, add=True)


async def remove_tool(username: str, tool: str) -> None:
    """removes a tool permission from the user"""
    await _modify_user_list(username, "tools", tool, add=False)
