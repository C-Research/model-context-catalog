## Why

MCC has per-tool resource limits (`limits:` in tool YAML — CPU/mem for the subprocess) but nothing that limits *call rate*. `ResponseLimitingMiddleware` caps response size; nothing caps request frequency. In a hosted free-trial scenario, marketplace tools (HTTP, scraping, shell) reachable through `execute()` can be hammered with zero cost to the caller and zero identity verification. This is the concrete fix for that gap.

## What Changes

- Add a `RateLimitMiddleware` to the MCP middleware chain (`mcc/app.py`), registered innermost (after `AuthMiddleware`, `LoggingMiddleware`, `TimingMiddleware`, `ResponseLimitingMiddleware`) so throttled calls are still logged and timed like any other call.
- Scope: catalog tools only, reached through the `execute` MCP tool (`context.message.name == "execute"`, subject resolved from `context.message.arguments["key"]`). The built-in verbs (`search`, `whoami`, `describe_tools`, `set_session`, `get_session`) are out of scope.
- New settings-only config block (`rate_limit:` in `mcc/settings.yaml`) — no `ToolModel`/tool-YAML field. Supports a global `default` and per-tool overrides under `tools: {<tool-key>: <value>}`, where each value is either a human-readable rate string `"<count>/<n><unit>"` (unit `s`/`min`/`hr`, e.g. `"60/1min"`, `"50/24hr"`) or `-1` for unlimited.
- Fixed-window rate limiting via a new small helper in `mcc/cache.py` built on cashews' `cache.incr`/`cache.get_expire` (not the `rate_limit`/`slice_rate_limit` decorators, which are shaped for a static per-function key, not a dynamic per-call key). A companion `parse_rate_limit()` helper converts the rate-string/-1 config values into `(limit, period_seconds)` once at middleware construction.
- On rejection, return a plain-text `ToolResult` (e.g. `"Rate limit exceeded for admin.shell — retry in 37s."`) — no error flag — matching `execute()`'s existing convention of returning informative strings (`"Unauthorized"`, validation errors) rather than raising.
- Feature is opt-in: `rate_limit.enabled: false` by default, so existing deployments are unaffected until configured.

## Capabilities

### New Capabilities

(none — this extends the existing middleware chain)

### Modified Capabilities

- `mcp-middleware`: adds a rate-limit middleware requirement alongside the existing auth/logging/timing middleware requirements.

## Impact

- `mcc/app.py` — register `RateLimitMiddleware` in the chain.
- `mcc/middleware.py` — new `RateLimitMiddleware` class.
- `mcc/cache.py` — new fixed-window rate-limit helper alongside `cached()`.
- `mcc/settings.yaml` — new `rate_limit:` block.
- No change to `mcc/models.py` (`ToolModel`) or tool YAML schema.
- No change to `execute()`'s own logic in `mcc/app.py` — rejection happens entirely in middleware before the handler runs.
