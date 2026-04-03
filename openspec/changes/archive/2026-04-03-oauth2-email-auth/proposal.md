## Why

Bearer tokens are manually managed secrets that require out-of-band distribution and rotation. Replacing them with OAuth2 delegates identity to a trusted provider, eliminates token management from MCC, and enables email-based user identity that maps naturally to how users are provisioned in most organizations.

## What Changes

- **BREAKING**: Bearer token generation and storage removed — existing tokens will stop working
- **BREAKING**: `username` field replaced by `email` as the primary user identifier in the DB and CLI
- `BearerAuthMiddleware` removed; FastMCP `MultiAuth` with a custom `TokenVerifier` wired as `mcp.auth`
- `get_user_by_email(email)` added to `auth.py` for identity lookup from JWT claims
- `get_current_user(ctx)` helper added — calls `get_access_token()`, extracts `email` from claims, returns user dict
- `search` and `execute` tools call `get_current_user(ctx)` instead of `ctx.get_state("current_user")`
- `create_user` CLI command takes `--email` instead of positional `username`, no longer prints a token
- `list-users` CLI output shows email instead of username

## Capabilities

### New Capabilities
- `oauth2-auth`: JWT-based authentication via FastMCP MultiAuth; extracts email claim and resolves MCC user for permission checks

### Modified Capabilities
- `bearer-auth-middleware`: Replaced entirely — auth is now handled by FastMCP's auth layer, not custom middleware
- `user-store`: `username` field removed, `email` field added as primary identifier; `token_hash` field removed
- `admin-cli`: `add-user` command takes `--email` instead of positional username arg; token output removed

## Impact

- `mcc/auth.py`: remove token fns, rename username→email, add `get_user_by_email`, add `get_current_user` helper
- `mcc/middleware.py`: deleted
- `mcc/app.py`: remove `add_middleware`, add `mcp.auth = MultiAuth(...)`
- `mcc/cli.py`: update `add-user`, `list-users`, `remove-user`, `grant`, `revoke` to use email
- TinyDB `users` table: schema migration (drop `username`, `token_hash`; add `email`)
- New dependency: a JWKS-compatible OAuth2 provider (configured via env vars)
