## Why

The tool catalog has no access control — any caller can search and execute any tool. RBAC with bearer token auth is needed to restrict tool access to authorized users and support multi-tenant or privileged tool deployments.

## What Changes

- New TinyDB-backed user store: users have a username, hashed bearer token, admin flag, group memberships, and explicit tool grants.
- New FastMCP middleware resolves the `Authorization: Bearer <token>` header to a user record on session init; user is stored in session state and never re-exposed.
- The `public` group is a reserved group — tools with `group: public` are accessible to unauthenticated callers. Authenticated users additionally access tools in their groups and explicit tool grants.
- New Click CLI (`mcc`) for all user and permission management: `add-user`, `remove-user`, `grant`, `revoke`. No MCP tools for auth management.
- `search` filters results to the caller's accessible tools only.
- `execute` enforces RBAC before dispatching — returns an error string for unauthorized calls.

## Capabilities

### New Capabilities
- `user-store`: TinyDB schema, token hashing, user CRUD operations
- `bearer-auth-middleware`: FastMCP middleware for bearer token resolution and session user injection
- `admin-cli`: Click CLI for user and permission management

### Modified Capabilities
- `search-tool`: Search now filters results to the caller's accessible tools
- `execute-tool`: Execute now enforces RBAC before dispatching

## Impact

- New file `mcc/auth.py` — TinyDB setup, token utilities, user CRUD
- New file `mcc/middleware.py` — BearerAuthMiddleware
- New file `mcc/cli.py` — Click CLI entry point
- `mcc/app.py` — search and execute updated for RBAC
- `main.py` — middleware registered on FastMCP app
- `pyproject.toml` — new dependencies: `tinydb`, `click`; new CLI script entry point
- Only works with HTTP-based MCP transports (SSE, streamable HTTP); STDIO has no headers
