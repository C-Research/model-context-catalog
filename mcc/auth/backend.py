import importlib
import inspect

from fastmcp.server.auth import RemoteAuthProvider
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.dependencies import get_access_token as fast_token

from mcc.auth.dev import get_admin_context as dev_admin
from mcc.auth.dev import get_public_context as dev_public
from mcc.settings import settings

_DEV_BACKENDS = {
    "dev-admin": dev_admin,
    "dev-public": dev_public,
}

_PROXY_PROVIDERS = {
    "github": ("fastmcp.server.auth.providers.github", "GitHubProvider"),
    "google": ("fastmcp.server.auth.providers.google", "GoogleProvider"),
    "azure": ("fastmcp.server.auth.providers.azure", "AzureProvider"),
    "auth0": ("fastmcp.server.auth.providers.auth0", "Auth0Provider"),
    "clerk": ("fastmcp.server.auth.providers.clerk", "ClerkProvider"),
    "discord": ("fastmcp.server.auth.providers.discord", "DiscordProvider"),
    "workos": ("fastmcp.server.auth.providers.workos", "WorkOSProvider"),
    "aws": ("fastmcp.server.auth.providers.aws", "AWSCognitoProvider"),
    "oci": ("fastmcp.server.auth.providers.oci", "OCIProvider"),
    "supabase": ("fastmcp.server.auth.providers.supabase", "SupabaseProvider"),
    "scalekit": ("fastmcp.server.auth.providers.scalekit", "ScalekitProvider"),
    "propelauth": ("fastmcp.server.auth.providers.propelauth", "PropelAuthProvider"),
    "descope": ("fastmcp.server.auth.providers.descope", "DescopeProvider"),
    "in-memory": ("fastmcp.server.auth.providers.in_memory", "InMemoryOAuthProvider"),
}


def _build_proxy_provider(name: str):
    module_path, class_name = _PROXY_PROVIDERS[name]
    cls = getattr(importlib.import_module(module_path), class_name)
    kwargs = {k: v for k, v in settings.oauth.to_dict().items() if v}
    return cls(**kwargs)


def _build_jwt_provider() -> RemoteAuthProvider:
    cfg = settings.jwt
    verifier = JWTVerifier(
        jwks_uri=cfg.get("jwks_uri") or None,
        issuer=cfg.get("issuer") or None,
        audience=cfg.get("audience") or None,
        required_scopes=cfg.get("required_scopes") or None,
    )
    return RemoteAuthProvider(
        token_verifier=verifier,
        authorization_servers=[cfg.authorization_server],
        base_url=cfg.base_url,
    )


def get_provider():
    auth = settings.auth
    if auth in _DEV_BACKENDS:
        return None
    if auth == "jwt":
        return _build_jwt_provider()
    if auth in _PROXY_PROVIDERS:
        return _build_proxy_provider(auth)
    raise ValueError(f"Unknown auth backend: {auth!r}")


async def get_user_context():
    """
    Displays full user context from auth provider.

    may contain sensitive info and crypto keys
    """
    auth = settings.auth
    if auth in _DEV_BACKENDS:
        return await _DEV_BACKENDS[auth]()
    token = fast_token()
    if inspect.isawaitable(token):
        return await token
    return token
