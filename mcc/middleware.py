import time

from fastmcp.server.middleware import Middleware, MiddlewareContext

from mcc.auth import get_current_user
from mcc.context import current_user_var
from mcc.settings import logger


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
