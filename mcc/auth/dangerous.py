from mcc.auth.db import list_users


async def get_user_context():
    for user in await list_users():
        if "admin" in user.groups:
            return user
    return None
