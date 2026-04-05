from elasticsearch import NotFoundError

from mcc.auth.models import UserModel
from mcc.db import UsersIndex


async def create_user(
    username: str,
    email: str | None = None,
    tools: list[str] | None = None,
    groups: list[str] | None = None,
) -> None:
    """creates a user and assigns their tools/groups perms"""
    async with UsersIndex() as _users:
        if await _users.get(username):
            raise ValueError(f"User '{username}' already exists")
        if email and await _users.search({"term": {"email": email}}):
            raise ValueError(f"Email '{email}' already exists")
        user = UserModel(
            username=username, email=email, groups=groups or [], tools=tools or []
        )
        await _users.put(username, user.model_dump())


async def delete_user(username: str) -> None:
    """deletes a user from the db"""
    async with UsersIndex() as _users:
        try:
            await _users.delete(username)
        except NotFoundError:
            raise ValueError(f"User '{username}' not found")


async def list_users() -> list[UserModel]:
    async with UsersIndex() as _users:
        docs = await _users.search({"match_all": {}})
        return [UserModel(**doc) for doc in docs]


async def get_user_by_username(username: str) -> UserModel | None:
    async with UsersIndex() as _users:
        doc = await _users.get(username)
        return UserModel(**doc) if doc else None


async def get_user_by_email(email: str) -> UserModel | None:
    async with UsersIndex() as _users:
        docs = await _users.search({"term": {"email": email}})
        return UserModel(**docs[0]) if docs else None


async def _update_user(username: str, user: UserModel) -> None:
    async with UsersIndex() as _users:
        await _users.put(username, user.model_dump())


async def add_group(username: str, group: str) -> None:
    """adds a user to a group"""
    user = await get_user_by_username(username)
    if user is None:
        raise ValueError(f"User '{username}' not found")
    if group not in user.groups:
        user.groups = user.groups + [group]
        await _update_user(username, user)


async def remove_group(username: str, group: str) -> None:
    """removes a user from a group"""
    user = await get_user_by_username(username)
    if user is None:
        raise ValueError(f"User '{username}' not found")
    if group not in user.groups:
        raise ValueError(f"User '{username}' is not a member of group '{group}'")
    user.groups = [g for g in user.groups if g != group]
    await _update_user(username, user)


async def add_tool(username: str, tool: str) -> None:
    """adds a tool permission to the user"""
    user = await get_user_by_username(username)
    if user is None:
        raise ValueError(f"User '{username}' not found")
    if tool not in user.tools:
        user.tools = user.tools + [tool]
        await _update_user(username, user)


async def remove_tool(username: str, tool: str) -> None:
    """removes a tool permission from the user"""
    user = await get_user_by_username(username)
    if user is None:
        raise ValueError(f"User '{username}' not found")
    if tool not in user.tools:
        raise ValueError(f"User '{username}' does not have tool '{tool}'")
    user.tools = [t for t in user.tools if t != tool]
    await _update_user(username, user)
