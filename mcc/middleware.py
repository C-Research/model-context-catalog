from fastmcp.server.middleware import Middleware, MiddlewareContext
from prometheus_client import Counter, Histogram

from mcc.auth import get_current_user
from mcc.cache import over_limit, parse_rate_limit
from mcc.context import ANONYMOUS_USER, UserModel, current_user_var
from mcc.models import ToolCallEvent, on_tool_call
from mcc.settings import logger, settings

TOOL_CALLS_TOTAL = Counter(
    "mcc_tool_calls_total", "Catalog tool calls, by tool key and outcome", ["tool", "status"]
)
TOOL_CALL_DURATION_SECONDS = Histogram(
    "mcc_tool_call_duration_seconds", "Catalog tool call duration in seconds", ["tool"]
)


def record_tool_call(tool_key: str, status: str, elapsed: float) -> None:
    """Records a completed catalog tool call into the shared Prometheus series.

    Called from the tool-call metrics hook below (registered on
    mcc.models.on_tool_call), so /metrics reflects tool calls made through
    either transport under the same series, keyed by exact tool key.
    """
    TOOL_CALLS_TOTAL.labels(tool=tool_key, status=status).inc()
    TOOL_CALL_DURATION_SECONDS.labels(tool=tool_key).observe(elapsed)


def display_username(user: UserModel) -> str:
    """Formats a user for log lines: 'anonymous', 'alice', or 'alice<a@b.com>'."""
    if user.is_anonymous:
        return "anonymous"
    if user.email:
        return f"{user.username}<{user.email}>"
    return user.username


def log_tool_call_start(username: str, tool_name: str, params) -> None:
    """Logs a tool call's parameters. Shared by the tool-call logging hook
    below and the rejected-call (rate-limit) log points in execute()/tool_execute()."""
    logger.info("%s calling %s with %s", username, tool_name, params)


def log_tool_call_end(username: str, tool_name: str, elapsed: float) -> None:
    """Logs a tool call's completion timing."""
    logger.info("%s completed %s in %.3fs", username, tool_name, elapsed)


def log_tool_call_throttled(username: str, tool_name: str, retry_after: int) -> None:
    """Logs a call rejected by the rate-limit check, before it ever reaches ToolModel.call()."""
    logger.info("%s throttled for %s — retry in %ss", username, tool_name, retry_after)


def _resolved_rate_limits() -> tuple[tuple[int, int], dict[str, tuple[int, int]]]:
    """Parses settings.rate_limit.default/.tools into (limit, period_seconds)
    pairs. Re-parsed on every call (parse_rate_limit is a cheap regex match)
    rather than cached, so tests can freely patch `mcc.middleware.settings`
    and app.py's startup validation call still validates every configured
    entry eagerly.
    """
    default = parse_rate_limit(settings.rate_limit.default)
    tools = {key: parse_rate_limit(value) for key, value in settings.rate_limit.tools.items()}
    return default, tools


def validate_rate_limit_settings() -> None:
    """Eagerly parses+validates every configured rate_limit entry, so a
    malformed value fails fast at process startup rather than on the first
    live request. Call once, at startup, when rate_limit.enabled is true."""
    _resolved_rate_limits()


async def check_rate_limit(tool_key: str, username: str) -> tuple[bool, int]:
    """Shared fixed-window rate-limit check for a (user, tool) pair.

    Called explicitly by execute() (before its cache lookup) and
    POST /tools/{key} (before invocation) — never from inside
    ToolModel.call(), since a cache hit must still count against the limit
    but never reaches call(). Both call sites share the exact same bucket key
    format (`ratelimit:{username}:{tool_key}`), so a caller's quota for a
    tool is one pool regardless of transport.
    """
    default, tools = _resolved_rate_limits()
    limit, period = tools.get(tool_key, default)
    key = f"ratelimit:{username}:{tool_key}"
    return await over_limit(key, limit, period)


class AuthMiddleware(Middleware):
    """Resolves the current user on every request and stashes in a contextvar."""

    async def on_message(self, context: MiddlewareContext, call_next):
        resolved = await get_current_user()
        current_user_var.set(resolved if resolved is not None else ANONYMOUS_USER)
        return await call_next(context)


@on_tool_call
async def _log_completed_call(event: ToolCallEvent) -> None:
    """Logs every call whose underlying callable actually ran, on either
    transport. A call rejected by the rate-limit check never reaches here —
    see log_tool_call_throttled, called explicitly at the rejection point."""
    username = display_username(event.user)
    log_tool_call_start(username, event.tool_key, event.params)
    log_tool_call_end(username, event.tool_key, event.duration)


@on_tool_call
async def _record_completed_call(event: ToolCallEvent) -> None:
    """Records mcc_tool_calls_total/mcc_tool_call_duration_seconds for every
    call whose underlying callable actually ran, on either transport. A call
    rejected by the rate-limit check or served from execute()'s result cache
    never reaches here — neither reaches ToolModel.call()."""
    record_tool_call(event.tool_key, event.status, event.duration)
