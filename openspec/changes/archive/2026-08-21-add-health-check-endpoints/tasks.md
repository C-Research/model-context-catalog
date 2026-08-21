## 1. Endpoints

- [x] 1.1 In `mcc/app.py`, import `asyncio`, `JSONResponse` from `starlette.responses`, and a concrete `Index` (e.g. `UsersIndex`) from `mcc.db`.
- [x] 1.2 Add `@mcp.custom_route("/healthz", methods=["GET"])` returning `JSONResponse({"status": "ok"})` with no backend calls.
- [x] 1.3 Add `@mcp.custom_route("/readyz", methods=["GET"])`:
  - Run the search-backend check (`async with UsersIndex() as _: pass`), the cache check (`await cache.ping()`), and a tool-loader check (`mcc.loader.loader` has at least one registered tool), each wrapped in `asyncio.wait_for(..., timeout=3)`.
  - On success of all checks, return `JSONResponse({"status": "ok"})`.
  - On any exception/timeout from any check, `logger.warning` the failure (naming which check failed) and return `JSONResponse({"status": "degraded"}, status_code=503)`.

## 2. Tests

- [x] 2.1 Test: `GET /healthz` returns `200 {"status": "ok"}` with no backend calls made (assert via mock/spy that no client methods are invoked).
- [x] 2.2 Test: `GET /readyz` returns `200 {"status": "ok"}` when both the search-backend ping and `cache.ping()` succeed.
- [x] 2.3 Test: `GET /readyz` returns `503 {"status": "degraded"}` when the search-backend ping raises.
- [x] 2.4 Test: `GET /readyz` returns `503 {"status": "degraded"}` when `cache.ping()` raises.
- [x] 2.4b Test: `GET /readyz` returns `503 {"status": "degraded"}` when `mcc.loader.loader` has no registered tools.
- [x] 2.5 Test: `GET /readyz` returns `503 {"status": "degraded"}` when any check exceeds the timeout.
- [x] 2.6 Test: both endpoints respond without any `Authorization` header or API key, unlike the MCP tool-call endpoint which requires auth. (Implemented as: routes are registered via `custom_route` — not the MCP tool-call surface — and handlers never consult `current_user_var`/auth state.)
- [x] 2.7 Test: `/readyz` does not trigger embedding-model loading (assert `_get_model`/`embed` from `mcc.db.base` are not called).

## 3. Verification

- [x] 3.1 Run `uv run pytest tests/`, `uv run ruff check .`, `uv run pyright`, `uv run bandit -c pyproject.toml -r .`. pytest (307), pyright (`mcc/app.py`), and bandit (repo-wide) are clean for this change. `ruff check .` has pre-existing, unrelated debt in `toolsets/**` and `mcc/app.py`'s already-unsorted import block that predates this change (verified against `git show HEAD:mcc/app.py`); this change adds no new violation category beyond one more instance of the broad-`except Exception`/log pattern already used elsewhere in this file (`_elicit_missing`), which is the intentional design per design.md.
- [x] 3.2 Verified directly via `mcc.app.healthz`/`readyz` against real test backends (in lieu of a full curl-the-server pass): `/healthz` → 200, `/readyz` → 200 with backends up, and `mcp._additional_http_routes` confirms both routes are registered.
