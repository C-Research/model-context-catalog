## Context

`mcc/routes.py` currently hand-rolls API-key extraction and gating per handler: `whoami` and `tools` each call `_extract_api_key`/`get_user_by_key` directly, and `require_admin` — a generalized admin-gating wrapper — is fully built and tested (`tests/test_app.py:690+`) but wired to zero routes. Enforcement for tool execution (rate limiting, call logging, response-size capping) lives entirely in `mcc/middleware.py` as FastMCP `Middleware` subclasses hooked on `on_call_tool`/`on_message`.

Source inspection of the installed `fastmcp` package confirms those hooks never fire for `custom_route` handlers: `FastMCP._run_middleware` (`fastmcp/server/server.py`) is invoked only from protocol dispatch methods (`call_tool`, `list_tools`, `read_resource`, `get_prompt`) and `low_level.py`. `custom_route` (`fastmcp/server/mixins/transport.py:100`) appends a plain Starlette `Route` to `_additional_http_routes`, spliced into the ASGI app's route list in `http.py` — wrapped only by genuine ASGI middleware (a separate list `mcp.add_middleware(...)` never touches). A REST tool-call endpoint added naively today would run with none of the enforcement the MCP `execute()` path already has.

## Goals / Non-Goals

**Goals:**
- One reusable `@route` decorator covering every auth shape currently needed by custom HTTP routes (none/optional/required/admin), replacing hand-rolled key extraction and the unused `require_admin`.
- Shared enforcement (rate limiting, logging, response-size capping, metrics) usable from both the MCP tool-call path and HTTP routes, so a REST tool call and an MCP tool call are enforced identically.
- REST access to tool execution (`POST /tools/{key}`), tool detail (`GET /tools/{key}`), user listing (`GET /users`), and metrics (`GET /metrics`), each gated appropriately.

**Non-Goals:**
- Session context or write-back for REST tool calls — `POST /tools/{key}` runs with an identity-only context in v1; no cookie/header-based HTTP session equivalent to MCP's `ctx.get_state`/`ctx.set_state` is being built.
- Full CRUD for user management over HTTP — only listing (`GET /users`); create/delete/grant/revoke remain CLI-only (`mcc user ...`).
- Per-tenant or grouped metric-label cardinality bucketing — `docs/future-features.md` #2 flagged this for a future multi-tenant hosting scenario that doesn't exist yet; v1 labels by exact tool key.
- Changing MCP transport-level auth (OAuth/JWT/dev backends) — `@route`'s key resolution stays independent of `settings.auth`/`get_provider()`, the same way `require_admin`/`get_user_by_key` already are.

## Decisions

**1. Three boolean kwargs (`admin`, `anonymous`, `optional`) rather than a single mode enum.**
`@route(admin=False, anonymous=False, optional=False)`. Considered a single `mode: Literal["anonymous", "optional", "required", "admin"]` — rejected because call sites read more naturally as booleans (`@route(admin=True)`) and `admin` already implies "required" without a redundant explicit mode value. `admin=True` combined with `anonymous=True` or `optional=True` is rejected at decoration time (`ValueError`, not a silent pick) — an ambiguous combination should fail at import time, not produce surprising runtime behavior.

**2. Resolved user is attached to `request.scope["user"]`, not passed as a handler argument.**
Handlers keep Starlette's native `(request) -> Response` signature — `custom_route` needs zero change to the handler shape — and read the resolved user via `request.user`, matching Starlette's own `Request.user` property (`self.scope["user"]`, confirmed in `starlette/requests.py:184`). Considered injecting `user` as the handler's first positional argument — rejected: it would require changing every handler's signature and diverge from the Starlette convention already visible via `request.state`/`request.user` elsewhere in the ecosystem.

**9. `@route(path, methods=None, ...)` registers directly onto `mcp` — no separate `ROUTES` list or `register_routes()` step.**
Each `@route(...)` call both declares (`path`/`methods`, default `["GET"]`) and gates a route in one place, calling `mcp.custom_route(path, methods=methods)(wrapper)` itself as the decorator applies — the call site is the single source of truth instead of a route's path/method living in two places (a decorator call and a separate registry entry). This requires `mcc/routes.py` to import `mcp` from `mcc.app` at module level, which is circular on its face (`mcc.app` also imports `mcc.routes`) — resolved by ordering: `mcc/app.py` constructs `mcp` and registers all its `mcp.add_middleware(...)` calls, *then* does a bare `import mcc.routes` (side-effecting, `# noqa: F401`) as the last step. By the time `mcc.routes` executes `from mcc.app import mcp`, `mcc.app`'s module object already has `mcp` bound, whether `mcc.app` or `mcc.routes` is whichever module gets imported first in a given process (verified both orderings manually). Considered extracting `mcp = FastMCP(...)` into its own dependency-free module (e.g. `mcc/mcp_instance.py`) to avoid the cycle entirely — rejected as unnecessarily invasive for this change: it would also require moving `lifespan`, `_session_store`, `_event_store_backend`, and `_branding` out of `app.py`, and the ordering-based resolution is a standard, well-understood pattern that keeps the diff scoped to `routes.py`/`app.py`.

**3. Key extraction: header first, `?api-key=` query param fallback.**
Extends the existing `_extract_api_key` (checks `X-API-Key`, then `Authorization: Bearer`) with a third fallback, the `api-key` query parameter, checked last. Header takes priority when both are present. Query-param support exists for clients that can't easily set custom headers; see Risks for the trade-off this introduces.

**4. Shared enforcement lives in plain functions in `mcc/middleware.py`, called by both transports.**
Because FastMCP's `Middleware` chain structurally cannot wrap a `custom_route` (Decision context above), the fix is to extract the logic each existing `Middleware.on_call_tool` implementation already contains — rate-limit check, call logging, response-size capping — into plain async functions, and have both the FastMCP `Middleware` subclasses and the new `@route`-decorated handlers call them. Considered wrapping the whole Starlette app in additional ASGI-level middleware that reimplements the same checks — rejected: that would duplicate logic under a different invocation shape (ASGI `scope`/`receive`/`send` vs. `MiddlewareContext`) rather than reuse it, and still needs the tool-key extracted from two different argument shapes (MCP `execute` arguments vs. REST path param) into one common check.

**5. Rate-limit bucket is shared verbatim between `execute()` and `POST /tools/{key}`.**
Same key format, `ratelimit:{username-or-anon}:{tool_key}` — a caller's throttling budget for a given tool is one pool regardless of transport. A REST path with its own separate bucket would let a caller double their effective quota by alternating transports.

**6. `GET`/`POST /tools/{key}` return `404` for both "unknown key" and "known key, access denied."**
Deliberately indistinguishable, so a REST caller can't use the endpoint to enumerate which admin-only tools exist by probing keys. An authenticated caller can already see exactly what they're allowed to call via `whoami`'s `tools` field or `GET /tools`, so this loses no legitimate capability — only the ability to distinguish "doesn't exist" from "not yours" on a single-item probe.

**7. `/metrics` labels by exact tool key.**
Matches the granularity `RateLimitMiddleware`'s bucket key and `LoggingMiddleware`'s log lines already use — all three enforcement/observability surfaces agree on what "a tool" is without inventing a second grouping concept. Revisit if the catalog's tool count or a multi-tenant dimension makes per-key cardinality a real cost (see Non-Goals).

**8. No session context for REST tool calls in v1.**
`execute()`'s context assembly and write-back are tied to an MCP `Context`'s `ctx.get_state`/`ctx.set_state`, which a plain `Request` doesn't have. `POST /tools/{key}` runs with `assemble_context(None, user)` — identity only, equivalent to a caller's first MCP call in a session with no stored vars. Tools that depend on stored session state or elicitation have no REST equivalent yet, same as elicitation already has no REST equivalent.

## Risks / Trade-offs

- **[Risk]** `?api-key=` query param exposes credentials more readily than a header (access logs, proxy logs, browser history, `Referer` leakage) → **[Mitigation]** header always takes priority; document the query param as a fallback for clients that can't set headers, not the recommended path.
- **[Risk]** Refactoring `mcc/middleware.py` touches the live, production MCP enforcement path → **[Mitigation]** behavior-preserving refactor only: existing `Middleware` subclasses become thin wrappers around the extracted functions with identical logic, verified against the existing `mcp-middleware` spec's scenarios before any new HTTP call site is added.
- **[Risk]** `POST /tools/{key}` without session context is a real capability gap relative to `execute()` for any tool that reads/writes session state → **[Mitigation]** explicit, documented v1 non-goal; such tools simply don't support the REST path yet.
- **[Risk]** New `prometheus_client` dependency → **[Mitigation]** small, widely used, no heavy transitive dependencies; low risk relative to the value of `/metrics`.
- **[Risk]** Route-ordering ambiguity between `/tools` and `/tools/{key}` → **[Mitigation]** none in practice — Starlette matches by exact pattern, and `ToolModel.key` (`".".join(groups + [name])`) is always dot-joined, never contains `/`, so no key can collide with the `/tools` list route.

## Migration Plan

- Additive for the new routes and decorator; no data migration.
- `require_admin` has zero call sites outside its own tests (confirmed via `grep`), so removing it is a no-op for runtime behavior; its tests are rewritten against `@route`.
- `mcc/middleware.py`'s refactor ships as one change with existing MCP-path tests passing unchanged against the extracted functions before the new HTTP call sites are added, to catch behavior drift at the source rather than at the new routes.
- No new settings required for the decorator; rate-limit sharing reuses `rate_limit.enabled`/`rate_limit.default`/`rate_limit.tools` unchanged.
- Rollback: revert the commit. No persisted state changes hands — Prometheus counters are in-process and ephemeral, not written to any index.

## Known Gap (deferred to a follow-up)

- **`MetricsMiddleware` was not confirmed working against a real running server for the MCP `execute()` path.** An in-memory `fastmcp.Client(mcp)` end-to-end test (this repo, same process) recorded `mcc_tool_calls_total`/`mcc_tool_call_duration_seconds` correctly for an `execute()` call. But against an actual running `mcc` server — restarted fresh both under Claude's stdio transport and separately via the CLI — calling a tool through the real MCP path did not produce any `mcc_tool_call*` series in `/metrics`, while calling the same tool through `POST /tools/{key}` did. Root cause not yet identified (candidates: middleware registration/ordering differing between transports in practice, a difference in how `context.message.arguments` is shaped over a real transport vs. the in-memory client, or something specific to the stdio/CLI invocation path). Needs investigation against a real running server before relying on `/metrics` for MCP-path tool-call observability.

## Open Questions

- Should `GET /metrics` be gated behind a setting (e.g. `metrics.enabled`, mirroring `rate_limit.enabled`) for deployments that don't want it exposed, or always-on like `/healthz`? Leaning always-on — it requires no credentials and reveals nothing more sensitive than aggregate call counts — but `rate_limit` set a precedent for an opt-in switch.
- Should Prometheus histogram buckets for `mcc_tool_call_duration_seconds` be customized via settings, or use the client library's defaults for v1? Leaning defaults until real latency data suggests otherwise.
