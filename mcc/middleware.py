import time

from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.tools import ToolResult

from mcc.auth import get_current_user
from mcc.cache import over_limit, parse_rate_limit
from mcc.context import current_user_var
from mcc.settings import logger, settings


class AuthMiddleware(Middleware):
    """Resolves the current user on every request and stashes in a contextvar."""

    async def on_message(self, context: MiddlewareContext, call_next):
        current_user_var.set(await get_current_user())
        return await call_next(context)


class LoggingMiddleware(Middleware):
    """Logs tool executions with user, tool key, params, and timing."""

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        user = current_user_var.get(None)
        username = "anonymous"
        if user:
            username = user.username
            if user.email:
                username = f"{username}<{user.email}>"
        tool_name = context.message.name
        params = context.message.arguments

        logger.info("%s calling %s with %s", username, tool_name, params)
        start = time.perf_counter()

        result = await call_next(context)

        elapsed = time.perf_counter() - start
        logger.info("%s completed %s in %.3fs", username, tool_name, elapsed)

        return result


class RateLimitMiddleware(Middleware):
    """Per-user, per-catalog-tool rate limiting for execute() calls.

    Catalog tools are never the MCP tool name itself (that's always
    "execute") — the subject is the `key` argument passed to execute(). Only
    execute() calls are rate limited; search/whoami/etc. are untouched.

    rate_limit.default and rate_limit.tools.* values are parsed once here
    (not per call) so a malformed settings.yaml entry (e.g. a typo'd unit)
    fails at middleware construction time, not on a live request.
    """

    def __init__(self):
        self._default = parse_rate_limit(settings.rate_limit.default)
        self._tools = {
            key: parse_rate_limit(value) for key, value in settings.rate_limit.tools.items()
        }

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        if context.message.name != "execute":
            return await call_next(context)

        tool_key = (context.message.arguments or {}).get("key")
        if not isinstance(tool_key, str):
            return await call_next(context)

        limit, period = self._tools.get(tool_key, self._default)

        user = current_user_var.get(None)
        username = user.username if user else "anon"
        key = f"ratelimit:{username}:{tool_key}"

        exceeded, remaining = await over_limit(key, limit, period)
        if exceeded:
            return ToolResult(
                f"Rate limit exceeded for {tool_key} — retry in {remaining}s."
            )
        return await call_next(context)
