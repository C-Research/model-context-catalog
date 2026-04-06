from mcc.auth.db import list_users
from mcc.auth.models import UserModel


async def _get_user_context(group: str) -> UserModel:
    for user in await list_users():
        if group in user.groups:
            return user
    return UserModel(username=f"dev-{group}", groups=[group])


async def get_admin_context() -> UserModel:
    """Selects the first admin user; falls back to a dummy admin user if none exist."""
    return await _get_user_context("admin")


async def get_public_context() -> UserModel:
    """Selects the first public user; falls back to a dummy public user if none exist."""
    return await _get_user_context("public")
