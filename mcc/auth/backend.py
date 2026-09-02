import importlib
import inspect
from datetime import datetime

from fastmcp.server.auth import RemoteAuthProvider, TokenVerifier
from fastmcp.server.auth.auth import AccessToken
from fastmcp.server.auth.oidc_proxy import OIDCProxy
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.dependencies import get_access_token as fast_token

from mcc.auth.dev import get_admin_context as dev_admin
from mcc.auth.dev import get_public_context as dev_public
from mcc.auth.keys import verify_api_key
from mcc.settings import logger, settings

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


def _build_client_storage(backend: str):
    """Build the AsyncKeyValue store for DCR client registrations/tokens/codes.

    Same URI convention as cache.backend/event_store.backend. redis is only
    imported when that backend is chosen, so mcc has no hard redis dependency.
    Any other scheme (e.g. "mem://") returns None, leaving FastMCP's own default
    (an encrypted file store) in place.
    """
    if backend.startswith(("redis://", "rediss://")):
        from key_value.aio.stores.redis import RedisStore

        return RedisStore(url=backend)
    return None


def _build_proxy_provider(name: str):
    module_path, class_name = _PROXY_PROVIDERS[name]
    cls = getattr(importlib.import_module(module_path), class_name)
    # dynaconf uppercases env-var-derived keys (MCC_OAUTH__FOO) unless a matching
    # lowercase key already exists in settings.yaml's defaults; lowercase here so
    # a provider kwarg missing from the defaults doesn't crash with e.g. AUDIENCE.
    # Drop only empty placeholders (unset string defaults), not False — several
    # real kwargs (verify_id_token, require_authorization_consent) are booleans
    # where False is a meaningful, intentional value, not "unset".
    kwargs = {
        k.lower(): v for k, v in settings.oauth.to_dict().items() if v not in (None, "")
    }
    # Defaults to cache.backend so a redis:// cache already covers DCR client
    # persistence with no extra config; set oauth.client_storage_backend only if
    # oauth state needs a different backend than the tool-call cache.
    client_storage_backend = kwargs.pop("client_storage_backend", "") or settings.cache.backend
    client_storage = _build_client_storage(client_storage_backend)
    if client_storage is not None:
        kwargs["client_storage"] = client_storage
    if kwargs.pop("verify_id_token", False):
        # Provider subclasses (Auth0Provider, AWSCognitoProvider, OCIProvider, ...)
        # don't expose verify_id_token, so build the underlying OIDCProxy directly
        # to verify the id_token instead of the access_token. Requires config_url
        # in settings.oauth, since providers that derive it internally (e.g. from
        # user_pool_id) can't be used here.
        # "openid" must be requested or the upstream IdP has no reason to issue an
        # id_token at all (Auth0Provider defaults to this; bypassing it here loses
        # that default, so it must be set explicitly). "email" must also be
        # requested or the id_token carries only sub/iss/aud — no email claim,
        # which mcc.auth.util.get_current_user requires to resolve the MCC user.
        kwargs.setdefault("required_scopes", ["openid", "email"])
        logger.info("%s: verifying id_token via OIDCProxy", name)
        return OIDCProxy(verify_id_token=True, **kwargs)
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


class ApiKeyVerifier(TokenVerifier):
    """Resolves a bearer API key to a username via the keys index.

    A thin credential→identity bridge: it places only the username in the
    returned ``AccessToken`` claims (never the raw key) and reads ES on every
    request so revocation is instant. All authorization comes from the users
    index downstream, unchanged.
    """

    async def verify_token(self, token: str) -> AccessToken | None:
        record = await verify_api_key(token)
        if record is None:
            return None
        raw_expiry = record.get("expires_at")
        expires_at = datetime.fromisoformat(raw_expiry) if raw_expiry else None
        # token carries the non-secret prefix, never the raw key: the
        # get_user_context admin tool surfaces this AccessToken to the LLM, so
        # nothing key-derived may live in token/claims/scopes.
        return AccessToken(
            token=f"mcc_{record['prefix']}",
            client_id=record["username"],
            scopes=[],
            expires_at=int(expires_at.timestamp()) if expires_at else None,
            claims={"login": record["username"]},
        )


def get_provider():
    auth = settings.auth
    if auth in _DEV_BACKENDS:
        return None
    if auth == "jwt":
        return _build_jwt_provider()
    if auth == "api_key":
        return ApiKeyVerifier()
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
