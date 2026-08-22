import asyncio
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Optional

from starlette.requests import Request
from starlette.responses import JSONResponse

from mcc.auth import get_user_by_key, whoami_info
from mcc.auth.models import UserModel
from mcc.cache import cache
from mcc.db import UsersIndex
from mcc.loader import loader
from mcc.settings import logger

_READYZ_TIMEOUT = 3


def _extract_api_key(request: Request) -> Optional[str]:
    """Extracts the raw key from `X-API-Key`, or `Authorization: Bearer <key>`, or None.

    `X-API-Key` takes precedence when both are present.
    """
    if api_key := request.headers.get("x-api-key"):
        return api_key
    scheme, _, raw_key = request.headers.get("authorization", "").partition(" ")
    return raw_key if scheme.lower() == "bearer" else None


def require_admin(
    handler: Callable[[Request, UserModel], Awaitable[JSONResponse]],
) -> Callable[[Request], Awaitable[JSONResponse]]:
    """Gates a custom_route handler on an admin API key, independent of settings.auth.

    Checks the raw key from `X-API-Key` or `Authorization: Bearer` against the
    mcc-keys index directly (see `get_user_by_key`) rather than going through
    `get_provider()`/`settings.auth` — so admin HTTP routes work the same
    whether the MCP transport is configured for jwt, an OAuth proxy, or dev
    mode. Responds 401 without calling `handler` if the key is
    missing/invalid/expired or doesn't belong to an admin user.
    """

    @wraps(handler)
    async def wrapper(request: Request) -> JSONResponse:
        raw_key = _extract_api_key(request)
        user = await get_user_by_key(raw_key, groups=["admin"]) if raw_key else None
        if user is None:
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await handler(request, user)

    return wrapper


async def healthz(request: Request) -> JSONResponse:
    """Liveness check: the process can handle an HTTP request. No backend calls."""
    return JSONResponse({"status": "ok"})


async def readyz(request: Request) -> JSONResponse:
    """Readiness check: the search backend, cache backend, and tool loader are all ready.

    Each check is bounded by _READYZ_TIMEOUT so a hung backend fails the probe
    quickly instead of holding the connection open. The specific failure is
    logged server-side only — the response body never names which backend
    failed, to avoid leaking internal topology to this unauthenticated route.
    """

    async def _check_search_backend() -> None:
        async with UsersIndex():
            pass

    async def _check_loader() -> None:
        if not len(loader):
            raise RuntimeError("tool loader has no tools registered")

    for name, check in (
        ("search backend", _check_search_backend),
        ("cache backend", cache.ping),
        ("tool loader", _check_loader),
    ):
        try:
            await asyncio.wait_for(check(), timeout=_READYZ_TIMEOUT)
        except Exception as exc:
            logger.warning("readyz: %s check failed: %s", name, exc)
            return JSONResponse({"status": "degraded"}, status_code=503)
    return JSONResponse({"status": "ok"})


async def whoami(request: Request) -> JSONResponse:
    """Identity + accessible-tools check, as JSON — the HTTP counterpart to the
    whoami MCP tool in app.py (same fields via whoami_info, rendered as text there).

    Open to any valid key, not just admins — unlike require_admin, this checks
    get_user_by_key with no `groups` filter, so any resolvable user passes.
    """
    raw_key = _extract_api_key(request)
    user = await get_user_by_key(raw_key) if raw_key else None
    if user is None:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    return JSONResponse(whoami_info(user))


ROUTES: list[tuple[str, list[str], Callable]] = [
    ("/healthz", ["GET"], healthz),
    ("/readyz", ["GET"], readyz),
    ("/whoami", ["GET"], whoami),
]


def register_routes(mcp) -> None:
    """Registers every custom HTTP route in ROUTES onto `mcp`."""
    for path, methods, handler in ROUTES:
        mcp.custom_route(path, methods=methods)(handler)
