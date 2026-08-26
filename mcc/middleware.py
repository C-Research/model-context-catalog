import time

from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.tools import ToolResult
from prometheus_client import Counter, Histogram

from mcc.auth import get_current_user
from mcc.cache import over_limit, parse_rate_limit
from mcc.context import current_user_var
from mcc.settings import logger, settings

TOOL_CALLS_TOTAL = Counter(
    "mcc_tool_calls_total", "Catalog tool calls, by tool key and outcome", ["tool", "status"]
)
TOOL_CALL_DURATION_SECONDS = Histogram(
    "mcc_tool_call_duration_seconds", "Catalog tool call duration in seconds", ["tool"]
)


def record_tool_call(tool_key: str, status: str, elapsed: float) -> None:
    """Records a completed catalog tool call into the shared Prometheus series.

    Called from both MetricsMiddleware (MCP execute()) and the POST
    /tools/{key} REST route, so /metrics reflects tool calls made through
    either transport under the same series, keyed by exact tool key.
    """
    TOOL_CALLS_TOTAL.labels(tool=tool_key, status=status).inc()
    TOOL_CALL_DURATION_SECONDS.labels(tool=tool_key).observe(elapsed)


def display_username(user) -> str:
    """Formats a resolved user (or None) for log lines: 'anonymous', 'alice', or 'alice<a@b.com>'."""
    if user is None:
        return "anonymous"
    if user.email:
        return f"{user.username}<{user.email}>"
    return user.username


def log_tool_call_start(username: str, tool_name: str, params) -> None:
    """Logs the start of a tool call. Shared by LoggingMiddleware (MCP) and
    the POST /tools/{key} REST route."""
    logger.info("%s calling %s with %s", username, tool_name, params)


def log_tool_call_end(username: str, tool_name: str, elapsed: float) -> None:
    """Logs the completion of a tool call. Shared by LoggingMiddleware (MCP)
    and the POST /tools/{key} REST route."""
    logger.info("%s completed %s in %.3fs", username, tool_name, elapsed)


def _resolved_rate_limits() -> tuple[tuple[int, int], dict[str, tuple[int, int]]]:
    """Parses settings.rate_limit.default/.tools into (limit, period_seconds)
    pairs. Re-parsed on every call (parse_rate_limit is a cheap regex match)
    rather than cached, so tests can freely patch `mcc.middleware.settings`
    and RateLimitMiddleware's construction-time call still validates every
    configured entry eagerly.
    """
    default = parse_rate_limit(settings.rate_limit.default)
    tools = {key: parse_rate_limit(value) for key, value in settings.rate_limit.tools.items()}
    return default, tools


async def check_rate_limit(tool_key: str, username: str) -> tuple[bool, int]:
    """Shared fixed-window rate-limit check for a (user, tool) pair.

    Used by both RateLimitMiddleware (MCP execute()) and POST /tools/{key},
    sharing the exact same bucket key format (`ratelimit:{username}:{tool_key}`)
    so a caller's quota for a tool is one pool regardless of transport.
    """
    default, tools = _resolved_rate_limits()
    limit, period = tools.get(tool_key, default)
    key = f"ratelimit:{username}:{tool_key}"
    return await over_limit(key, limit, period)


class AuthMiddleware(Middleware):
    """Resolves the current user on every request and stashes in a contextvar."""

    async def on_message(self, context: MiddlewareContext, call_next):
        current_user_var.set(await get_current_user())
        return await call_next(context)


class LoggingMiddleware(Middleware):
    """Logs tool executions with user, tool key, params, and timing."""

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        user = current_user_var.get(None)
        username = display_username(user)
        tool_name = context.message.name
        params = context.message.arguments

        log_tool_call_start(username, tool_name, params)
        start = time.perf_counter()

        result = await call_next(context)

        elapsed = time.perf_counter() - start
        log_tool_call_end(username, tool_name, elapsed)

        return result


class RateLimitMiddleware(Middleware):
    """Per-user, per-catalog-tool rate limiting for execute() calls.

    Catalog tools are never the MCP tool name itself (that's always
    "execute") — the subject is the `key` argument passed to execute(). Only
    execute() calls are rate limited; search/whoami/etc. are untouched.
    """

    def __init__(self):
        # Eagerly parses+validates every configured entry at construction time
        # (app startup), so a malformed rate_limit entry fails fast rather
        # than on the first live request.
        _resolved_rate_limits()

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        if context.message.name != "execute":
            return await call_next(context)

        tool_key = (context.message.arguments or {}).get("key")
        if not isinstance(tool_key, str):
            return await call_next(context)

        user = current_user_var.get(None)
        username = user.username if user else "anon"

        exceeded, remaining = await check_rate_limit(tool_key, username)
        if exceeded:
            return ToolResult(
                f"Rate limit exceeded for {tool_key} — retry in {remaining}s."
            )
        return await call_next(context)


class MetricsMiddleware(Middleware):
    """Records mcc_tool_calls_total/mcc_tool_call_duration_seconds for every
    catalog tool call made through the MCP execute() tool.

    Scoped to `execute` calls only (like RateLimitMiddleware), keyed by the
    catalog tool key rather than the MCP verb name, so metrics track catalog
    tool calls specifically. Always registered, independent of rate_limit.enabled,
    so /metrics works under the default configuration.
    """

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        if context.message.name != "execute":
            return await call_next(context)

        tool_key = (context.message.arguments or {}).get("key")
        if not isinstance(tool_key, str):
            return await call_next(context)

        start = time.perf_counter()
        try:
            result = await call_next(context)
        except Exception:
            record_tool_call(tool_key, "error", time.perf_counter() - start)
            raise
        record_tool_call(tool_key, "success", time.perf_counter() - start)
        return result
