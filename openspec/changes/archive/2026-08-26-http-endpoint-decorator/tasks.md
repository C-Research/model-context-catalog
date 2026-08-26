## 1. Dependencies

- [x] 1.1 Add `prometheus_client` to `pyproject.toml` dependencies and run `uv lock`/`uv sync`.

## 2. Shared enforcement in mcc/middleware.py

- [x] 2.1 Extract the rate-limit check (bucket key, window logic, limit resolution) out of `RateLimitMiddleware.on_call_tool` into a standalone async function, e.g. `check_rate_limit(tool_key, username) -> (exceeded, remaining)`, called by `RateLimitMiddleware` unchanged.
- [x] 2.2 Extract the call-logging body out of `LoggingMiddleware.on_call_tool` into a standalone function, e.g. `log_tool_call(username, tool_key, params, elapsed)`, called by `LoggingMiddleware` unchanged.
- [x] 2.3 Add metrics instrumentation via `prometheus_client`: `mcc_tool_calls_total{tool,status}` counter and `mcc_tool_call_duration_seconds{tool}` histogram, plus a shared `record_tool_call(tool_key, status, elapsed)` function called from both the existing MCP-path hooks and the new REST path.
- [x] 2.4 Run the existing `mcp-middleware` test suite against the refactored functions to confirm MCP-path behavior is unchanged before any new HTTP call site is added.

## 3. @route decorator

- [x] 3.1 Extend `_extract_api_key` in `mcc/routes.py` to check the `api-key` query parameter as a third fallback, after the existing `X-API-Key`/`Authorization: Bearer` header checks.
- [x] 3.2 Implement `@route(path, methods=None, *, admin=False, anonymous=False, optional=False)` in `mcc/routes.py`: resolves the user per mode, attaches it to `request.scope["user"]`, registers directly onto `mcp` via `mcp.custom_route` (no separate `ROUTES` list/registration function), and invokes the handler with its existing `(request) -> Response` signature. Raises at decoration time if `admin=True` is combined with `anonymous=True` or `optional=True`.
- [x] 3.3 Remove `require_admin` and its tests in `tests/test_app.py`. Add tests covering all four `@route` modes (default/required, `anonymous`, `optional`, `admin`) and the contradictory-kwargs rejection (moved to new `tests/test_routes.py`, alongside the other routes.py tests below).

## 4. Retrofit existing routes onto @route

- [x] 4.1 Retrofit `whoami` onto `@route("/whoami")` (default: required, non-admin), reading `request.user` instead of calling `get_user_by_key` directly.
- [x] 4.2 Retrofit `tools` (the `GET /tools` list handler) onto `@route("/tools", optional=True)`.
- [x] 4.3 Retrofit `healthz`/`readyz` onto `@route("/healthz"|"/readyz", anonymous=True)`.
- [x] 4.4 Re-run the existing `tools-http-endpoint` and `health-check-endpoints` test suites to confirm no behavior drift from the retrofit (updated `tests/test_health.py`'s `_REQ` sentinel to a real minimal `Request`, since `@route` now touches `request.scope` even in anonymous mode — all 10 tests pass).

## 5. /tools/{key} GET+POST

- [x] 5.1 Add `GET /tools/{key}` handler (`@route("/tools/{key}", optional=True)`): `404` for an unknown key or `!tool.allows(request.user)`, otherwise the same serialized shape as one `GET /tools` entry.
- [x] 5.2 Add `POST /tools/{key}` handler (`@route("/tools/{key}", ["POST"], optional=True)`): same `404` rule as 5.1; parse the JSON request body as params, call `tool.call(**params)` with an identity-only context (`assemble_context(None, request.user)`), return the result as plain text.
- [x] 5.3 Wire `POST /tools/{key}` through the shared rate-limit check from 2.1, using the same `ratelimit:{username-or-anon}:{tool_key}` bucket as MCP `execute()`.
- [x] 5.4 Wire `POST /tools/{key}` through the shared logging/metrics functions from 2.2/2.3.
- [x] 5.5 Implement error responses for `POST /tools/{key}`: plain-text body, full traceback when `settings.DEBUG` is `true`, otherwise a one-line message, for both validation errors and unexpected exceptions.

## 6. /users endpoint

- [x] 6.1 Add `GET /users` handler (`@route("/users", admin=True)`) calling `list_users()`.
- [x] 6.2 Support `?keys=true` to include each user's `.key` field in the response; omit it by default.

## 7. /metrics endpoint

- [x] 7.1 Add `GET /metrics` handler (`@route("/metrics", anonymous=True)`) returning `prometheus_client.generate_latest()` with the correct `Content-Type`.

## 8. Tests

- [x] 8.1 Add tests for `GET`/`POST /tools/{key}`: unknown key, inaccessible key, successful call, validation error with `settings.DEBUG` on and off, rate-limit bucket sharing with `execute()` (`tests/test_routes.py`).
- [x] 8.2 Add tests for `GET /users`: non-admin rejection, admin success, `keys=` default vs. `true` (`tests/test_routes.py`).
- [x] 8.3 Add tests for `GET /metrics`: anonymous access, counters reflecting recorded tool calls (shared `record_tool_call` used by both transports) (`tests/test_routes.py`).

## 9. Verification

- [x] 9.1 Run `uv run pytest`, `uv run pyright`, `uv run ruff check .`, and `uv run bandit -c pyproject.toml -r .` — all four pass (454 tests passed; pyright's 6 errors are pre-existing in `toolsets/`, confirmed via `git stash`; ruff and bandit clean).
