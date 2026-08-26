## Why

Every custom HTTP route in `mcc/routes.py` hand-rolls its own API-key extraction and auth gating (`whoami`, `tools`), while a generalized admin-gating helper (`require_admin`) was already built and tested but wired to zero routes. Meanwhile, tool execution's enforcement — rate limiting, call logging, response-size capping — only runs on the MCP `execute()` path: FastMCP's `Middleware` chain (`_run_middleware`) is invoked exclusively from protocol dispatch in `fastmcp/server/server.py` and never for `custom_route` handlers. That blocks safely adding REST access to tool execution, user listing, or metrics — a REST tool-call endpoint added today would bypass every enforcement mechanism the MCP path already relies on.

## What Changes

- Add an `@route(admin=False, anonymous=False, optional=False)` decorator in `mcc/routes.py`. It resolves the caller's API key (`X-API-Key` or `Authorization: Bearer` header first, falling back to an `?api-key=` query parameter — header always wins), and attaches the resolved user to `request.scope["user"]` (read inside handlers as `request.user`, matching Starlette's existing `Request.user` convention). Four modes: `anonymous` never attempts key resolution (user is always `None`); `optional` resolves if a key is present but never requires one; the default requires a resolved user (`401` otherwise); `admin` requires a resolved user in the `admin` group (`401`/`403` otherwise). `admin=True` combined with `anonymous=True` or `optional=True` is rejected at decoration time. **BREAKING**: removes the unused `require_admin` helper and changes how `whoami`/`tools`/`healthz`/`readyz` resolve auth internally (external behavior of these four routes is unchanged).
- Extract the enforcement already used by the MCP `execute()` path — rate limiting, call logging, response-size capping — out of the `Middleware` subclasses in `mcc/middleware.py` into plain shared functions, so both the FastMCP tool-call path and the new `@route`-decorated HTTP routes invoke the same enforcement instead of a REST path silently running with none of it.
- Add `GET /tools/{key}` (single tool detail, reusing the existing tool-serialization shape) and `POST /tools/{key}` (executes the tool via REST, returning its result as plain text) to the tools HTTP surface. Both `404` when the key is unknown *or* the caller lacks access — indistinguishable, so the response never confirms a gated tool's existence. `POST` shares its rate-limit bucket (`ratelimit:{username}:{tool_key}`) with the MCP `execute` tool for the same catalog key. Failure responses are plain text: a full traceback when `settings.DEBUG` is true, otherwise a one-line message. No session context or write-back in v1 — the call runs with an identity-only context (no `set_session`/`get_session` state).
- Add `GET /users`, admin-gated, listing users via the existing `list_users()`. Defaults to omitting each user's `.key` metadata; `?keys=true` includes it (`{"prefix", "created_at", "expires_at"}`, never the hash or raw key).
- Add `GET /metrics`, anonymous, exposing Prometheus-format counters/histograms (`mcc_tool_calls_total{tool,status}`, `mcc_tool_call_duration_seconds{tool}`) recorded by the shared enforcement layer for both the MCP `execute()` path and the new `POST /tools/{key}` path — one label per exact tool key, matching the granularity the rate-limit bucket already uses.

## Capabilities

### New Capabilities
- `http-endpoint-auth`: the `@route` decorator, its four auth modes, and the shared API-key extraction (header + query-param fallback) used by every custom HTTP route.
- `users-http-endpoint`: admin-gated `GET /users` listing with optional key metadata.
- `metrics-endpoint`: `GET /metrics` Prometheus exposition, fed by both the MCP and REST tool-call paths.

### Modified Capabilities
- `tools-http-endpoint`: adds `GET /tools/{key}` and `POST /tools/{key}`. Existing `GET /tools` behavior (listing, formats, anonymous access to public tools) is unchanged.
- `mcp-middleware`: the rate-limit middleware's bucket is now shared with `POST /tools/{key}` calls against the same tool key; adds a metrics-recording requirement feeding `/metrics`.

## Impact

- `mcc/routes.py`: new `@route` decorator; `whoami`/`tools`/`healthz`/`readyz` retrofitted onto it; dead `require_admin` removed; new `/tools/{key}` (GET+POST), `/users`, `/metrics` handlers.
- `mcc/middleware.py`: rate limiting, logging, and response-size enforcement refactored into shared functions callable from both `Middleware.on_call_tool` implementations and the new HTTP handlers; adds metrics recording.
- `mcc/auth/util.py`: `get_user_by_key`'s key-resolution logic becomes the shared implementation `@route` calls.
- New dependency: a Prometheus client library (e.g. `prometheus_client`) for `/metrics` — not currently in `pyproject.toml`.
- Tests: `tests/test_app.py` (existing `require_admin` tests rewritten against `@route`), `tests/test_health.py`.
