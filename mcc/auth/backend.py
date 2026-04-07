import inspect

from fastmcp.server.dependencies import get_access_token as fast_token

from mcc.auth.github_pat import get_user_context as pat_token
from mcc.auth.github_oauth import get_provider
from mcc.auth.dev import (
    get_admin_context as dev_admin,
    get_public_context as dev_public,
)
from mcc.settings import settings

backends = {
    "github_oauth": fast_token,
    "github_pat": pat_token,
    "dev-admin": dev_admin,
    "dev-public": dev_public,
}
providers = {
    "github_oauth": get_provider,
    "github_pat": None,
    "dev-admin": None,
    "dev-public": None,
}


async def get_user_context():
    """
    Displays full user context from auth provider.

    may contain sensitive info and crypto keys
    """
    if settings.auth not in backends:
        raise ValueError(f"auth backed {settings.auth} not supported")
    backend = backends[settings.auth]()
    if inspect.isawaitable(backend):
        return await backend
    return backend


def get_auth():
    if settings.auth not in providers:
        raise ValueError(f"auth provider {settings.auth} not found")
    return providers[settings.auth]
