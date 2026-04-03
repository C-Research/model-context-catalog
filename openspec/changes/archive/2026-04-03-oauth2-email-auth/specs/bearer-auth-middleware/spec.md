## REMOVED Requirements

### Requirement: Bearer token resolved at session init
**Reason**: Replaced by FastMCP `MultiAuth` + custom `TokenVerifier`. JWT validation and identity resolution are now handled by the FastMCP auth layer; `BearerAuthMiddleware` is deleted.
**Migration**: `get_current_user(ctx)` in `auth.py` provides equivalent identity resolution. Call it at the top of any tool that needs the current user instead of reading `ctx.get_state("current_user")`.

### Requirement: Token never propagated beyond middleware
**Reason**: The JWT token is now managed entirely by FastMCP's auth layer. The `AccessToken` object (not the raw token string) is what tool handlers interact with via `get_access_token()`.
**Migration**: No action required. The FastMCP auth layer enforces this boundary.

### Requirement: Middleware registered on FastMCP app
**Reason**: `BearerAuthMiddleware` is deleted. Auth registration is now `mcp.auth = MultiAuth(...)` in `app.py`.
**Migration**: Remove any `mcp.add_middleware(BearerAuthMiddleware)` call.
