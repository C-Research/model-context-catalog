## 1. Settings

- [x] 1.1 Add `rate_limit:` block to `mcc/settings.yaml` under `default:` (`enabled: false`, `default: "60/1min"`, `tools: {}`), with a comment documenting the rate-string format (`"<count>/<n><unit>"`, unit `s|min|hr`), the `-1` = unlimited sentinel, and the multi-pod counting caveat (mirroring the existing `event_store.backend` comment style).

## 2. Cache helper

- [x] 2.1 Add a fixed-window rate-limit helper to `mcc/cache.py` (`async def over_limit(key: str, limit: int, period: int) -> tuple[bool, int]`, returning whether the call is over limit and the seconds remaining in the current window), built on `cache.incr(key, expire=period)` and `cache.get_expire(key)`. Treat `limit == -1` as always-not-over-limit without touching the cache.
- [x] 2.2 Add `parse_rate_limit(value: int | str) -> tuple[int, int]` to `mcc/cache.py`, converting a `rate_limit.yaml` value into `(limit, period_seconds)`: `-1` → `(-1, 0)`; `"<count>/<n><unit>"` (unit `s|min|hr`) → `(count, n * unit_seconds)`. Raise `ValueError` on anything else.

## 3. Middleware

- [x] 3.1 Add `RateLimitMiddleware` to `mcc/middleware.py`:
  - `__init__`: parse `settings.rate_limit.default` and every `settings.rate_limit.tools.*` entry once via `parse_rate_limit`, caching the resulting `(limit, period)` tuples on the instance — a malformed value fails at construction, not on a live request.
  - `on_call_tool`: return early (call through) if `context.message.name != "execute"`.
  - Extract `tool_key = context.message.arguments.get("key")`; return early (call through) if missing or not a `str`.
  - Resolve `(limit, period)` from the pre-parsed per-tool dict, falling back to the pre-parsed default.
  - Resolve the current user via `current_user_var`, build the key `f"ratelimit:{user.username if user else 'anon'}:{tool_key}"`.
  - Call the `mcc/cache.py` helper from task 2.1; on over-limit, return `ToolResult(f"Rate limit exceeded for {tool_key} — retry in {n}s.")` without calling `call_next`.
  - On within-limit, call and return `await call_next(context)`.
- [x] 3.2 In `mcc/app.py`, register `RateLimitMiddleware` last in the `mcp.add_middleware(...)` sequence (after `ResponseLimitingMiddleware`), gated on `settings.get("rate_limit", {}).get("enabled", False)` — only add it when enabled.

## 4. Tests

- [x] 4.1 Test: rate limiting disabled (no config, or `enabled: false`) never registers the middleware / never throttles.
- [x] 4.2 Test: calls within the configured limit pass through and the underlying tool executes.
- [x] 4.3 Test: a call exceeding the limit returns the plain-text rejection message and does not invoke the underlying tool.
- [x] 4.4 Test: fixed-window reset — after `period` seconds (or with a mocked/advanced clock) elapse from the first call in a window, the counter resets and calls succeed again.
- [x] 4.5 Test: tool-specific entry in `rate_limit.tools` overrides `rate_limit.default` for that tool key.
- [x] 4.6 Test: `limit: -1` (tool-specific or default) never throttles and never touches the counter.
- [x] 4.7 Test: missing/non-string `key` argument on an `execute` call skips the rate-limit check and reaches `execute()`'s own "Unknown tool" handling.
- [x] 4.8 Test: `search`, `whoami`, `describe_tools`, `set_session`, `get_session` are never throttled regardless of settings.
- [x] 4.9 Test: two distinct anonymous callers to the same tool share one counter (`anon` bucket).
- [x] 4.10 Test: a call served from `execute()`'s own result cache (`cache_ttl`) still increments the rate-limit counter.
- [x] 4.11 Test: a throttled call still produces the normal `LoggingMiddleware`/`TimingMiddleware` log lines.
- [x] 4.12 Test: `parse_rate_limit` on each valid form (`"60/1min"`, `"50/24hr"`, `"10/30s"`, `-1`) returns the expected `(limit, period_seconds)`.
- [x] 4.13 Test: `parse_rate_limit` on malformed input (bad unit, missing `/`, non-numeric count, empty string) raises `ValueError`.

## 5. Verification

- [x] 5.1 Run `uv run pytest tests/`, `uv run ruff check .`, `uv run pyright`, `uv run bandit -c pyproject.toml -r .`. pytest: 319 passed (307 + 12 new `parse_rate_limit` cases). bandit: clean. pyright: `mcc/app.py`/`mcc/cache.py`/`mcc/middleware.py` all 0 errors (verified against baseline via `git show HEAD:<file>`). ruff: `mcc/middleware.py` clean; `mcc/cache.py` has its one pre-existing `UP035` (unrelated to this change); `tests/test_mcp_features.py` has pre-existing `FakeMessage`/`FakeContext` duck-typing debt this change doesn't add to structurally (same RUF012/I001 count as after the initial implementation).
- [ ] 5.2 Manually exercise via `scripts/test_get_current_user.py`-style script or existing MCP test client: configure a low limit for a real tool, confirm the rejection message and reset behavior end-to-end.
