import asyncio
from collections.abc import Awaitable, Callable
from functools import wraps

from starlette.requests import Request
from starlette.responses import JSONResponse

from mcc.auth import get_user_by_key
from mcc.auth.models import UserModel
from mcc.cache import cache
from mcc.db import UsersIndex
from mcc.loader import loader
from mcc.settings import logger

_READYZ_TIMEOUT = 3


def require_admin(
    handler: Callable[[Request, UserModel], Awaitable[JSONResponse]],
) -> Callable[[Request], Awaitable[JSONResponse]]:
    """Gates a custom_route handler on an admin API key, independent of settings.auth.

    Checks the raw key in the `Authorization: Bearer` header against the
    mcc-keys index directly (see `get_user_by_key`) rather than going through
    `get_provider()`/`settings.auth` — so admin HTTP routes work the same
    whether the MCP transport is configured for jwt, an OAuth proxy, or dev
    mode. Responds 401 without calling `handler` if the key is
    missing/invalid/expired or doesn't belong to an admin user.
    """

    @wraps(handler)
    async def wrapper(request: Request) -> JSONResponse:
        scheme, _, raw_key = request.headers.get("authorization", "").partition(" ")
        user = (
            await get_user_by_key(raw_key, groups=["admin"])
            if scheme.lower() == "bearer"
            else None
        )
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


@require_admin
async def admin_whoami(request: Request, user: UserModel) -> JSONResponse:
    """Sanity check: resolves the caller's admin API key and echoes their user record."""
    return JSONResponse(user.model_dump())


ROUTES: list[tuple[str, list[str], Callable]] = [
    ("/healthz", ["GET"], healthz),
    ("/readyz", ["GET"], readyz),
    ("/admin/whoami", ["GET"], admin_whoami),
]


def register_routes(mcp) -> None:
    """Registers every custom HTTP route in ROUTES onto `mcp`."""
    for path, methods, handler in ROUTES:
        mcp.custom_route(path, methods=methods)(handler)
