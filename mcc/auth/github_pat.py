import httpx

from mcc.settings import settings


def get_user_context():
    response = httpx.get(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {settings.github_pat.token}"},
    )
    return response.json()
