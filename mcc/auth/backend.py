from fastmcp.server.dependencies import get_access_token as fast_token

from mcc.auth.github_pat import get_user_context as pat_token
from mcc.auth.github_oauth import get_provider
from mcc.auth.dangerous import get_user_context as danger
from mcc.settings import settings

backends = {
    "github_oauth": fast_token,
    "github_pat": pat_token,
    "dangerous": danger,
}
providers = {
    "github_oauth": get_provider,
    "github_pat": None,
    "dangerous": None,
}


def get_user_context():
    """
    Displays full user context from auth provider.

    may contain sensitive info and crypto keys
    """
    return backends[settings.auth]()


def get_auth():
    return providers[settings.auth]
