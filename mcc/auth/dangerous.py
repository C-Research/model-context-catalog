from mcc.auth.db import list_users


def get_user_context():
    for user in list_users():
        if user["group"] == "admin":
            return user
    raise ValueError("no admin users created")
