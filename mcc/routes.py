import asyncio
import json
import traceback
from collections.abc import Awaitable, Callable
from functools import wraps
from pathlib import Path

from markdown_it import MarkdownIt
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    PLATFORM_COLLECTOR,
    REGISTRY,
    generate_latest,
)
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    Response,
)

# app.py constructs `mcp` before its own `import mcc.routes` (placed after
# mcp's construction and middleware registration specifically so this works),
# so `mcp` already exists on the partially-initialized mcc.app module by the
# time this line runs — the standard way to break a two-module import cycle.
# Needed here (not deferred to a function) because @route registers each
# route directly via mcp.custom_route at decoration time.
from mcc.app import mcp
from mcc.audit import _record_search
from mcc.auth import get_user_by_key, list_users, whoami_info
from mcc.cache import cache
from mcc.context import (
    ANONYMOUS_USER,
    NO_WRITEBACK,
    UserModel,
    assemble_context,
    current_context_var,
    current_user_var,
    writeback_context_var,
)
from mcc.db import UsersIndex
from mcc.loader import loader
from mcc.middleware import check_rate_limit, display_username, log_tool_call_throttled
from mcc.models import ToolModel
from mcc.settings import logger, settings

_markdown = MarkdownIt()

# prometheus_client auto-registers this onto REGISTRY at import time; it emits
# a python_info metric with the exact major/minor/patchlevel. /metrics is
# unauthenticated, so left registered it'd hand any caller the precise Python
# patch version — useful for targeting a known CVE in that patch.
REGISTRY.unregister(PLATFORM_COLLECTOR)

_READYZ_TIMEOUT = 3


def _extract_api_key(request: Request) -> str | None:
    """Extracts the raw key from `X-API-Key`, `Authorization: Bearer <key>`,
    or the `api-key` query parameter, in that order.

    A header always takes priority over the query parameter when both are
    present. The query parameter exists for clients that can't easily set
    custom headers; prefer a header where possible since query parameters are
    more likely to be captured in access logs, proxy logs, or browser history.
    """
    if api_key := request.headers.get("x-api-key"):
        return api_key
    scheme, _, raw_key = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() == "bearer":
        return raw_key
    return request.query_params.get("api-key")


def route(
    path: str,
    methods: list[str] | None = None,
    *,
    admin: bool = False,
    anonymous: bool = False,
    optional: bool = False,
) -> Callable[
    [Callable[[Request], Awaitable[Response]]], Callable[[Request], Awaitable[Response]]
]:
    """Decorator that both declares and gates a custom HTTP route.

    Registers `path`/`methods` (default `["GET"]`) directly onto `mcp` via
    `mcp.custom_route`, and wraps the handler so it resolves the caller's
    identity from an API key and gates the route according to its declared
    mode, attaching the resolved user (or ANONYMOUS_USER) to
    `request.scope["user"]` — read inside handlers as `request.user`,
    matching Starlette's own `Request.user` convention — before invoking the
    handler, which keeps its native `(request) -> Response` signature.

    Modes:
      (default) a resolved user is required; responds `401` if the key is
        missing, invalid, or expired.
      anonymous=True: never attempts key resolution — `request.user` is
        always ANONYMOUS_USER, regardless of what credentials the request
        carries.
      optional=True: resolves a key if present, but never requires one —
        `401` is never returned for a missing/invalid key.
      admin=True: requires a resolved user in the `admin` group; responds
        `401` if no user resolves, or if the resolved user isn't an admin.
        Incompatible with `anonymous=True`/`optional=True` — raises at
        decoration time rather than picking one silently.
    """
    if admin and (anonymous or optional):
        raise ValueError(
            "route(admin=True) cannot be combined with anonymous=True or optional=True"
        )

    def decorator(
        handler: Callable[[Request], Awaitable[Response]],
    ) -> Callable[[Request], Awaitable[Response]]:
        @wraps(handler)
        async def wrapper(request: Request) -> Response:
            if anonymous:
                request.scope["user"] = ANONYMOUS_USER
                current_user_var.set(ANONYMOUS_USER)
                return await handler(request)
            raw_key = _extract_api_key(request)
            groups = ["admin"] if admin else None
            resolved = await get_user_by_key(raw_key, groups=groups) if raw_key else None
            if resolved is None and not optional:
                return JSONResponse({"error": "unauthorized"}, status_code=401)
            user = resolved if resolved is not None else ANONYMOUS_USER
            request.scope["user"] = user
            # Mirrors AuthMiddleware's job for the MCP transport: Starlette runs each
            # request in its own asyncio task, so this can't leak across requests, the
            # same reason current_context_var/writeback_context_var already work this
            # way in tool_execute below. Makes identity uniformly readable from
            # ToolModel.call()'s hook regardless of which transport called it.
            current_user_var.set(user)
            return await handler(request)

        return mcp.custom_route(path, methods=methods or ["GET"])(wrapper)

    return decorator


@route("/healthz", anonymous=True)
async def healthz(request: Request) -> JSONResponse:
    """Liveness check: the process can handle an HTTP request. No backend calls."""
    return JSONResponse({"status": "ok"})


@route("/readyz", anonymous=True)
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
        except Exception as exc:  # noqa: BLE001
            logger.warning("readyz: %s check failed: %s", name, exc)
            return JSONResponse({"status": "degraded"}, status_code=503)
    return JSONResponse({"status": "ok"})


@route("/whoami")
async def whoami(request: Request) -> JSONResponse:
    """Identity + accessible-tools check, as JSON — the HTTP counterpart to the
    whoami MCP tool in app.py (same fields via whoami_info, rendered as text there).
    """
    return JSONResponse(whoami_info(request.user))


def _accessible_tools(user: UserModel) -> list[ToolModel]:
    """Tools `user` can access, sorted by key. ANONYMOUS_USER yields public tools only."""
    return user.accessible_tools


def _lookup_accessible_tool(key: str, user: UserModel) -> ToolModel | None:
    """Returns the tool for `key` if it exists and `user` can access it, else
    None — the shared 404-masking lookup for both /tools/{key} routes, so a
    caller can't distinguish "no such tool" from "not yours"."""
    tool = loader.get(key)
    if tool is None or not tool.allows(user):
        return None
    return tool


def _serialize_tool(tool: ToolModel) -> dict:
    """JSON-safe tool detail: same fields as tool_signature.md, no execution internals."""
    return {
        "key": tool.key,
        "groups": tool.sorted_groups,
        "params": [
            {
                "name": p.name,
                "type": p.type,
                "required": p.required,
                "default": p.default,
                "description": p.description,
                "example": p.example,
            }
            for p in tool.visible_params
        ],
        "return_type": "str | (int, str, str)"
        if tool.exec
        else (tool.return_type or "unknown"),
        "description": tool.description,
        "example": tool.example,
    }


@route("/tools", optional=True)
async def tools(request: Request) -> JSONResponse | PlainTextResponse | HTMLResponse:
    """Lists the caller's accessible tools, detailed, in JSON (default), markdown, or HTML.

    No auth required — a missing/invalid key resolves to ANONYMOUS_USER, which
    tool.allows() already scopes to public tools only (same anonymous
    behavior search()/describe_tools() have as MCP tools).
    """
    accessible = _accessible_tools(request.user)

    fmt = request.query_params.get("format", "json")
    if fmt == "md":
        return PlainTextResponse("\n\n".join(t.signature for t in accessible))
    if fmt == "html":
        markdown = "\n\n".join(t.signature for t in accessible)
        return HTMLResponse(_markdown.render(markdown))
    return JSONResponse([_serialize_tool(t) for t in accessible])


@route("/tools/{key}", optional=True)
async def tool_detail(request: Request) -> JSONResponse:
    """GET /tools/{key}: a single tool's detail, same shape as one GET /tools
    entry. 404s for an unknown key or one the caller can't access —
    indistinguishable, so probing keys can't enumerate gated tools.
    """
    tool = _lookup_accessible_tool(request.path_params["key"], request.user)
    if tool is None:
        return JSONResponse({"error": "not found"}, status_code=404)
    return JSONResponse(_serialize_tool(tool))


def _error_text(exc: Exception) -> str:
    """Plain-text error body: the full traceback when settings.DEBUG is true,
    otherwise a one-line `Type: message` summary."""
    if settings.get("DEBUG", False):
        return "".join(traceback.format_exception(exc))
    return f"{type(exc).__name__}: {exc}"


@route("/tools/{key}", ["POST"], optional=True)
async def tool_execute(request: Request) -> PlainTextResponse:
    """POST /tools/{key}: executes the tool with the JSON request body as its
    parameters, returning the result as plain text. Same 404 masking as
    tool_detail for an unknown or inaccessible key.

    Runs with an identity-only context (no stored session state, no
    write-back) — v1 has no HTTP session equivalent to MCP's
    ctx.get_state/set_state. Shares its rate-limit bucket with the MCP
    execute tool for the same key. Errors are plain text: the full traceback
    when settings.DEBUG is true, otherwise a one-line message.
    """
    key = request.path_params["key"]
    user = request.user
    tool = _lookup_accessible_tool(key, user)
    if tool is None:
        return PlainTextResponse("Not found", status_code=404)

    raw_body = await request.body()
    try:
        params = json.loads(raw_body) if raw_body else {}
    except json.JSONDecodeError as exc:
        return PlainTextResponse(_error_text(exc), status_code=400)
    if not isinstance(params, dict):
        return PlainTextResponse("Request body must be a JSON object", status_code=400)

    username = user.username
    if settings.get("rate_limit", {}).get("enabled", False):
        exceeded, remaining = await check_rate_limit(key, username)
        if exceeded:
            log_tool_call_throttled(username, key, remaining)
            return PlainTextResponse(
                f"Rate limit exceeded for {key} — retry in {remaining}s.",
                status_code=429,
            )

    context = assemble_context(None, user)
    context_token = current_context_var.set(context)
    writeback_token = writeback_context_var.set(NO_WRITEBACK)
    try:
        result = await tool.call(**params)
    except ValidationError as exc:
        return PlainTextResponse(_error_text(exc), status_code=400)
    except Exception as exc:  # noqa: BLE001
        logger.exception("REST execution of %s failed", key)
        return PlainTextResponse(_error_text(exc), status_code=500)
    finally:
        writeback_context_var.reset(writeback_token)
        current_context_var.reset(context_token)

    return PlainTextResponse(str(result))


@route("/users", admin=True)
async def users_list(request: Request) -> JSONResponse:
    """GET /users: lists all users. Admin-gated. `?keys=true` includes each
    user's `.key` metadata (`{"prefix", "created_at", "expires_at"}`, never
    the hash or raw key); omitted by default.
    """
    include_keys = request.query_params.get("keys", "").lower() == "true"
    users = await list_users()
    exclude = set() if include_keys else {"key"}
    return JSONResponse([u.model_dump(exclude=exclude) for u in users])


@route("/metrics", anonymous=True)
async def metrics(request: Request) -> Response:
    """GET /metrics: Prometheus text-exposition of tool-call counters and
    duration histograms, fed by both the MCP execute() path and
    POST /tools/{key}."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@route("/search", optional=True)
async def search_tools(request: Request) -> JSONResponse:
    """GET /search?q=...&min_score=...: natural-language tool search over the
    caller's accessible tools — the HTTP counterpart to the search MCP tool
    in app.py, with the same scoring and audit behavior.
    """
    query = request.query_params.get("q", "")
    raw_min_score = request.query_params.get("min_score")
    try:
        min_score = float(raw_min_score) if raw_min_score is not None else None
    except ValueError:
        return JSONResponse({"error": "min_score must be a number"}, status_code=400)

    results = await loader.search(query, min_score)
    allowed = [(t, s) for t, s in results if t.allows(request.user)]
    if settings.AUDIT_SEARCH_INDEX:
        await _record_search(
            display_username(request.user),
            query,
            min_score,
            [(t.key, s) for t, s in allowed],
        )
    return JSONResponse([{"score": s, **_serialize_tool(t)} for t, s in allowed])


@route("/ui{path:path}", anonymous=True)
async def ui(request: Request) -> Response:
    """The optional built-in web UI: the built SPA's entry point at exactly
    `/ui`, and its static assets underneath (e.g. `/ui/assets/index-abc.js`).

    Always registered like every other route here; gated at request time
    instead of at import time. `/ui` itself needs no auth — the SPA
    authenticates its own API calls via a client-held key, not this route.

    404s, rather than crashing startup, when `settings.ui_enabled` is off or
    the SPA was never built (`mcc/static/ui/index.html` missing) — same
    degrade-don't-crash posture as readyz. No SPA-fallback for unmatched
    sub-paths by design: there is no client-side router to hand them to.
    """
    if not settings.get("ui_enabled", False):
        return PlainTextResponse("Not found", status_code=404)

    ui_dir = Path(__file__).with_name("static") / "ui"

    # "{path:path}" is greedy and matches immediately after "ui" with no
    # separator, so without this check "/uifoo" would match too (path="foo").
    # Require an empty path (bare "/ui") or one starting with "/".
    raw_path = request.path_params["path"]
    if raw_path and not raw_path.startswith("/"):
        return PlainTextResponse("Not found", status_code=404)

    rel = raw_path.lstrip("/") or "index.html"
    target = (ui_dir / rel).resolve()
    if ui_dir.resolve() not in (target, *target.parents):
        return PlainTextResponse("Not found", status_code=404)
    if not target.is_file():
        if rel == "index.html":
            logger.warning(
                "ui_enabled is true but %s is missing (run `make ui`)", target
            )
        return PlainTextResponse("Not found", status_code=404)
    return FileResponse(target)
