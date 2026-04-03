from fastmcp.server.dependencies import get_http_request
from fastmcp.server.middleware import Middleware

from .auth import get_user_by_token


class BearerAuthMiddleware(Middleware):
    async def on_initialize(self, context, call_next):
        user = None
        try:
            request = get_http_request()
            auth = request.headers.get("authorization", "")
            if auth.startswith("Bearer "):
                token = auth[7:]
                user = get_user_by_token(token)
        except Exception:
            pass
        ctx = context.fastmcp_context
        if ctx is not None:
            await ctx.set_state("current_user", user, serializable=True)
        return await call_next(context)
