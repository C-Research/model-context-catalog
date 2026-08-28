## Why

MCC has no persisted, queryable record of who called which tool, with what parameters, when, or with what outcome — only ephemeral process log lines. Building that as a fourth place bolting observability onto tool execution would compound an existing problem: `LoggingMiddleware`, `RateLimitMiddleware`, and `MetricsMiddleware` each independently wrap the MCP `execute` verb *and* are separately duplicated as inline calls in the `POST /tools/{key}` REST handler, because every catalog tool call already funnels through one real choke point — `ToolModel.call()` — that none of them actually use. Adding a persisted audit log is the forcing function to fix that: give `ToolModel.call()` a hook mechanism, move the concerns that belong there (logging, metrics, and the new audit trail) onto it, and keep only rate limiting — which has a hard pre-cache timing requirement — as an explicit pre-check.

## What Changes

- Add an opt-in persisted audit trail: `AuditIndex` (new, in `mcc/audit.py`), gated by a new `audit_index` setting (`""` default = disabled; any non-empty value both enables auditing and names the index).
- Add `audit_params` setting (bool, default `true`) — when `false`, audit rows omit the params field entirely rather than writing it empty.
- Each audit row (when enabled) records: username (or none), API key prefix (when resolved via one), tool key, visible params serialized as `key=var;key=var` text (when `audit_params` is true), start time, duration, and status (`success`/`error`) with a one-line `Type: message` error summary on failure — never a full traceback, regardless of `settings.DEBUG`.
- Add a hook registry to `ToolModel` (`models.py`): a `ToolCallEvent` dataclass and `on_tool_call()` registration, fired once per invocation from inside `ToolModel.call()`'s existing try/except, carrying tool key, resolved user (via `current_user_var`), key prefix, visible params, duration, and status/error.
- **Delete `LoggingMiddleware` and `MetricsMiddleware`** (FastMCP `Middleware` classes) and their inline REST-route counterparts (`log_tool_call_start/end`, `record_tool_call` calls in `tool_execute`); replace both with hooks registered against `on_tool_call`, fired uniformly for both the MCP `execute` path and `POST /tools/{key}`.
  - **Behavior change:** a cache-hit `execute()` call (served from `cache_ttl` without invoking the callable) is no longer logged or metrics-recorded. Previously both middlewares wrapped the entire `execute()` verb, including cache hits; the hook only fires when `ToolModel.call()` actually runs. Rate limiting is unaffected (see below) — a cache hit still counts against it.
- **Delete `RateLimitMiddleware`** (the FastMCP `Middleware` class) but keep its check exactly where enforcement runs today: an explicit `check_rate_limit()` call before the cache lookup in `execute()` and before invocation in `tool_execute()`. This is deliberately *not* folded into the `ToolModel.call()` hook — doing so would break the existing "cache hit still counts against the rate limit" requirement, since a cache hit never reaches `call()`.
- Populate `UserModel.key` (`{"prefix", "created_at", "expires_at"}`) at per-request identity resolution time — `get_current_user()` for the MCP `api_key` backend, `get_user_by_key()` for REST — not just in `list_users()`'s batch admin view. Needed so an audit row can record which key authenticated the call.
- `route()` (routes.py) now sets `current_user_var` alongside the existing `request.scope["user"] = user`, so identity is uniformly readable via the contextvar on both the MCP and REST transports (today only `AuthMiddleware` sets it, for MCP only).
- Rename the concrete `ESIndex`/`OSIndex` classes (`mcc/db/es.py`, `mcc/db/os.py`) to `IndexBase` and export it from `mcc/db/__init__.py`'s existing backend dispatch, so `AuditIndex` (and any future optional index) can subclass one name without its own ES/OS branching.

## Capabilities

### New Capabilities
- `tool-call-audit-log`: opt-in, persisted, append-only record of catalog tool calls that actually execute (or fail), covering the `audit_index`/`audit_params` settings, the recorded fields, and the redaction/error-verbosity rules.

### Modified Capabilities
- `mcp-middleware`: the Logging, Metrics, and Rate limit requirements are re-described around the hook-based implementation — Logging/Metrics are no longer literally FastMCP `Middleware` classes and no longer observe cache-hit `execute()` calls; Rate limit enforcement is no longer literally "middleware" (an explicit pre-cache check instead) but its behavior, including cache-hit-still-counts, is unchanged.
- `execute-tool`: logging is no longer "handled by middleware" (that wording is removed); the handler now explicitly checks the rate limit before its cache lookup and explicitly logs a throttled call at the point it rejects one.

`tools-http-endpoint` is not listed as modified: its own spec never described logging/metrics as implementation detail (that's entirely owned by `mcp-middleware`'s requirements, which already cover both transports), and its rate-limit-sharing requirement is behaviorally unchanged — `tool_execute()` gains one explicit log call on rejection, same as `execute()`, which is covered by the `mcp-middleware` delta.

## Impact

- `mcc/models.py` — `ToolCallEvent`, `on_tool_call`/hook registry, `ToolModel.call()` fires hooks.
- `mcc/audit.py` (new) — `AuditIndex`, the audit hook consumer, `audit_index`/`audit_params` gating.
- `mcc/middleware.py` — `LoggingMiddleware`, `MetricsMiddleware`, `RateLimitMiddleware` classes removed; logging/metrics hook functions added; `AuthMiddleware` unchanged.
- `mcc/app.py` — `execute()` gains an explicit pre-cache rate-limit check; middleware registration list shrinks to `AuthMiddleware`/`TimingMiddleware`/`ResponseLimitingMiddleware`; imports `mcc.audit` for its registration side effect.
- `mcc/routes.py` — `route()` sets `current_user_var`; `tool_execute()` drops its inline success-path logging/metrics calls, keeps its rate-limit check, and gains an explicit log call on rejection (previously missing on this transport).
- `mcc/auth/util.py` — `get_current_user()`, `get_user_by_key()` populate `UserModel.key` on resolution.
- `mcc/db/es.py`, `mcc/db/os.py`, `mcc/db/__init__.py` — `ESIndex`/`OSIndex` renamed to `IndexBase`, exported from `mcc/db`.
- `mcc/settings.yaml` — `audit_index: ""`, `audit_params: true`.
- `tests/test_mcp_features.py` — tests referencing the deleted middleware classes need rewriting against the new hook-based behavior.
