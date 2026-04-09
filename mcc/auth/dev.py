from mcc.auth.db import list_users
from mcc.auth.models import UserModel
from mcc.settings import logger


async def _get_user_context(group: str) -> UserModel:
    try:
        users = await list_users()
    except Exception:
        logger.warning("Unable to list users, ES users index might b blank.")
        users = []
    for user in users:
        if group in user.groups:
            return user
    return UserModel(username=f"dev-{group}", groups=[group])


async def get_admin_context() -> UserModel:
    """Selects the first admin user; falls back to a dummy admin user if none exist."""
    return await _get_user_context("admin")


async def get_public_context() -> UserModel:
    """Selects the first public user; falls back to a dummy public user if none exist."""
    return await _get_user_context("public")
