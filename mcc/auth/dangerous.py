from mcc.auth.db import list_users


async def get_user_context():
    """Selects the first admin user if found"""
    for user in await list_users():
        if "admin" in user.groups:
            return user
