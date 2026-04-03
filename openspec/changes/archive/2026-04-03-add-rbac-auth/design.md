## Context

The tool catalog currently has no access control. Any caller can search and execute any tool. This change introduces RBAC using bearer tokens, TinyDB for user storage, and FastMCP middleware for token resolution. Management is entirely CLI-driven — no MCP tools for auth.

FastMCP 3.x exposes a `Middleware` base class with `on_initialize` and `on_call_tool` hooks. The `get_http_request()` helper from `fastmcp.server.dependencies` provides access to HTTP headers (including `Authorization`) during `on_initialize`. `ctx.set_state()` / `ctx.get_state()` provide session-scoped state for passing the resolved user to tool functions.

**Constraint**: Bearer token auth requires HTTP transport (SSE or streamable HTTP). STDIO transport has no HTTP headers and cannot carry auth.

## Goals / Non-Goals

**Goals:**
- Bearer token → user resolution in FastMCP middleware at session init
- Token never appears in tool params, responses, or session state keys beyond the middleware
- `public` group is reserved and open to unauthenticated callers
- search and execute enforce RBAC using the session user
- CLI (`mcc`) is the sole interface for user and permission management

**Non-Goals:**
- MCP tools for auth management
- Token rotation or expiry
- OAuth / OIDC / JWT — plain opaque tokens only
- STDIO transport auth
- Rate limiting or audit logging

## Decisions

### TinyDB with embedded user document
```json
{
  "username": "alice",
  "token_hash": "sha256:<hex>",
  "is_admin": false,
  "groups": ["ops"],
  "tools": ["special_tool"]
}
```
Groups and tools are embedded lists on the user document. TinyDB is document-oriented — embedded is simpler than normalized tables and reads are a single lookup.

**Alternative considered**: Separate `memberships` and `permissions` tables. Rejected — adds multi-query overhead with no relational benefit at this scale.

### SHA-256 token hashing (no salt)
Tokens are random 32-byte hex strings (256 bits entropy). They are hashed with SHA-256 for storage. No salt needed — the token itself has sufficient entropy to defeat rainbow tables.

**Alternative considered**: bcrypt. Rejected — bcrypt is designed for low-entropy passwords. For high-entropy tokens, SHA-256 is fast and appropriate.

### Token generated once at `add-user`, never retrievable
`mcc add-user` generates the token, prints it to stdout once, stores the hash. No retrieve/rotate commands. If lost, remove and re-add the user.

### Middleware resolves token in `on_initialize`, stores user in session state
```
on_initialize:
  header = get_http_request().headers.get("Authorization", "")
  token = strip "Bearer " prefix
  user = tinydb_lookup(sha256(token))
  ctx.set_state("current_user", user_without_token_hash)  # serializable=True
  if no token or no match: ctx.set_state("current_user", None)
```
Session-scoped state persists across all tool calls in the same MCP session — token is validated once per connection, not per call.

**Alternative considered**: Validate token in `on_call_tool` per request. Rejected — more TinyDB lookups, and the session is already established at `on_initialize`.

### `public` group is reserved — implicit open access
Tools with `group: public` are accessible without auth. No user needs to be granted the public group. The RBAC check is:
```
can_access(user, tool_entry):
  if tool_entry["group"] == "public": return True
  if user is None: return False
  return tool_entry["group"] in user["groups"] or tool_name in user["tools"]
```

### CLI only — no MCP auth management tools
All user/permission management goes through the Click CLI. The MCP surface stays minimal: `search` and `execute` only.

### `mcc` CLI entry point via pyproject.toml scripts
```toml
[project.scripts]
mcc = "mcc.cli:cli"
```
Commands: `add-user`, `remove-user`, `grant`, `revoke`.
`grant` and `revoke` accept `--group` and/or `--tool`; at least one is required.

## Risks / Trade-offs

- **Session-scoped auth**: If a user's permissions change mid-session, the session retains the old user snapshot until reconnect. Mitigation: acceptable for this use case; document the behavior.
- **TinyDB file contention**: CLI writes and server reads share the same TinyDB file. TinyDB uses file locking — low risk for the expected write frequency (CLI ops are rare vs. server reads).
- **Token loss = user re-creation**: No recovery path if a token is lost. Mitigation: clear CLI message at `add-user` time: "Save this token — it will not be shown again."
- **HTTP transport only**: STDIO callers get no auth. Mitigation: documented constraint; STDIO is typically trusted local use.

## Migration Plan

1. Add `tinydb` and `click` to `pyproject.toml`
2. Create `mcc/auth.py` — TinyDB setup, token utilities, `can_access`
3. Create `mcc/middleware.py` — `BearerAuthMiddleware`
4. Create `mcc/cli.py` — Click CLI
5. Update `mcc/app.py` — RBAC in `search` and `execute`
6. Update `main.py` — register middleware
7. Update `pyproject.toml` — CLI script entry point
