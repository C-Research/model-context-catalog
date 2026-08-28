## 1. Settings

- [x] 1.1 Add `audit_index: ""` to `mcc/settings.yaml`, with a comment documenting that empty disables auditing and any non-empty value both enables it and names the index.
- [x] 1.2 Add `audit_params: true` to `mcc/settings.yaml`, with a comment documenting that `false` omits the params field from audit records.

## 2. `IndexBase` rename in `mcc/db`

- [x] 2.1 In `mcc/db/es.py`, rename `ESIndex` to `IndexBase`; update `UsersIndex`/`KeysIndex`/`ToolIndex` to subclass `IndexBase`.
- [x] 2.2 In `mcc/db/os.py`, rename `OSIndex` to `IndexBase`; update `UsersIndex`/`KeysIndex`/`ToolIndex` to subclass `IndexBase`.
- [x] 2.3 In `mcc/db/__init__.py`, export `IndexBase = _backend.IndexBase` alongside the existing `UsersIndex`/`KeysIndex`/`ToolIndex`/`session_store` dispatch.

## 3. Hook mechanism on `ToolModel`

- [x] 3.1 In `mcc/models.py`, add a `ToolCallEvent` dataclass: `tool_key`, `user` (`UserModel | None`), `key_prefix` (`str | None`), `params` (`dict | None`), `started_at`, `duration`, `status` (`"success" | "error"`), `error` (`str | None`).
- [x] 3.2 Add `on_tool_call(fn)` (registers, returns `fn`) and an internal hook list; add a `_fire_call_hooks(event)` helper that awaits each registered hook and catches/logs any exception per hook without propagating.
- [x] 3.3 Update `ToolModel.call()`: read `current_user_var` for the caller, snapshot `visible_params` values (not `call_kwargs`, which includes hidden/override values) before invoking, time the invocation, and call `_fire_call_hooks(...)` in a `finally` block after the existing try/except, with `status`/`error` set appropriately on the exception path.

## 4. Key-prefix plumbing

- [x] 4.1 In `mcc/auth/util.py`'s `get_current_user()`, after resolving identity (any backend), populate `user.key = {"prefix": ...}` via a direct `KeysIndex().get(user.username)` lookup — independent of which backend authenticated this request, since a user who normally logs in via OAuth/JWT may still have a provisioned API key on file.
- [x] 4.2 In `mcc/auth/util.py`'s `get_user_by_key()`, populate `user.key = {"prefix": ...}` from the `record` already returned by `verify_api_key` before returning the `UserModel`.
- [x] 4.3 Update `UserModel.key`'s docstring/comment (`mcc/auth/models.py`) — no longer populated only by `list_users()`'s batch enrichment.

## 5. `mcc/audit.py` (new)

- [x] 5.1 Import `IndexBase` from `mcc.db`; define `AuditIndex(IndexBase)` with `index = settings.AUDIT_INDEX` and a mapping covering timestamp/username/key_prefix/tool_key/params/status/error/duration fields.
- [x] 5.2 Add an `on_tool_call`-registered consumer that: serializes `event.params` as `key=var;key=var` text when `settings.AUDIT_PARAMS` is true (omits the field otherwise), writes one document (`id=str(uuid4())`) to `AuditIndex`, and catches/logs any write failure without raising.
- [x] 5.3 Only register that consumer if `settings.AUDIT_INDEX` is non-empty at import time — auditing disabled means the hook never runs, not just no-ops per call.

## 6. `mcc/middleware.py` cleanup

- [x] 6.1 Delete the `LoggingMiddleware`, `RateLimitMiddleware`, and `MetricsMiddleware` classes.
- [x] 6.2 Add an `on_tool_call`-registered logging hook (username/tool key/params/duration), replacing `LoggingMiddleware`'s behavior for calls that reach `ToolModel.call()`.
- [x] 6.3 Add an `on_tool_call`-registered metrics hook that records `mcc_tool_calls_total`/`mcc_tool_call_duration_seconds` from `ToolCallEvent`, replacing `MetricsMiddleware`.
- [x] 6.4 Keep `check_rate_limit`/`_resolved_rate_limits`/`parse_rate_limit` usage as-is (still called explicitly, not from inside a middleware class) — no relocation needed since `execute()`/`tool_execute()` already import from `middleware.py` today.
- [x] 6.5 Leave `AuthMiddleware` unchanged.

## 7. `mcc/app.py` wiring

- [x] 7.1 Remove the `mcp.add_middleware(LoggingMiddleware())`, `mcp.add_middleware(RateLimitMiddleware())` (and its `rate_limit.enabled` conditional), and `mcp.add_middleware(MetricsMiddleware())` lines.
- [x] 7.2 In `execute()`, before the `cached(...)` lookup: if `settings.rate_limit.enabled`, call `check_rate_limit(tool.key, username)`; on exceeded, log the rejection explicitly and return the same throttled-response text `RateLimitMiddleware` used to produce, without touching the cache.
- [x] 7.3 Add `import mcc.audit` (for its registration side effect), following the same pattern as the existing `import mcc.routes`.

## 8. `mcc/routes.py` wiring

- [x] 8.1 In `route()`'s wrapper, set `current_user_var.set(user)` alongside the existing `request.scope["user"] = user` (and for the `anonymous=True` branch, alongside `request.scope["user"] = None`).
- [x] 8.2 In `tool_execute()`, remove the inline `record_tool_call`/`log_tool_call_start`/`log_tool_call_end` calls on the success/failure paths (now handled by the hooks via `ToolModel.call()`).
- [x] 8.3 In `tool_execute()`'s rate-limit-exceeded branch, add an explicit log call before returning the `429` response (this transport had none before).

## 9. Tests

- [x] 9.1 Update `tests/test_mcp_features.py`: remove/rewrite tests that import or instantiate `LoggingMiddleware`/`RateLimitMiddleware`/`MetricsMiddleware` directly against the new hook-based behavior. (Also fixed `tests/test_app.py`'s `test_rate_limit_middleware_not_registered_when_disabled`, the one other direct reference.)
- [x] 9.2 Add tests: hook fires on success and on error from `ToolModel.call()`; hook does not fire on a cache hit; hook does not fire on a rate-limited call; `current_user_var` is set inside a REST route handler.
- [x] 9.3 Add tests for `mcc/audit.py`: no write when `audit_index` is unset; a write occurs (with expected fields) when set; params omitted when `audit_params` is `false`; hidden/override params never appear; error field is a one-liner even with `settings.DEBUG` true; an unreachable audit backend doesn't fail the triggering tool call. (New `tests/test_audit.py`.)
- [x] 9.4 Add key-prefix tests: `get_current_user()`/`get_user_by_key()` populate `user.key["prefix"]` when resolved via an API key; remain `None` for OAuth/JWT/dev auth.
- [x] 9.5 Extend `conftest.py`'s isolated test-index setup/teardown to cover an audit test index (mirroring `mcc-users-test`/`mcc-tools-test`), enabling `audit_index` for the relevant tests only.

## 10. Verification

- [x] 10.1 Run `uv run pytest`, `uv run pyright`, `uv run ruff check .`, `uv run bandit -c pyproject.toml -r .` — fix any issues. (467 tests pass; `mcc/` pyright-clean — the 6 pyright errors in `toolsets/` are pre-existing on `main`, unrelated to this change; ruff and bandit clean repo-wide.)
- [x] 10.2 Manually verify against a local Elasticsearch: with `audit_index` set, call a tool via MCP `execute` and via `POST /tools/{key}`, confirm one audit row per call with the expected fields; set `audit_params: false` and confirm params are omitted; unset `audit_index` and confirm no rows are written. (All four scenarios verified live: MCP row, REST row, params omitted, hook not registered at all when disabled.)
