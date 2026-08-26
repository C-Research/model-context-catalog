## 1. Endpoint

- [x] 1.1 In `mcc/routes.py`, add a helper that returns the accessible tool list for a user: `[t for t in loader.values() if t.allows(user)]`, sorted by `t.key` — the same predicate `search()`/`describe_tools()` already use in `mcc/app.py`.
- [x] 1.2 Add a JSON serializer for one `ToolModel`: `{"key": tool.key, "groups": tool.sorted_groups, "params": [...], "return_type": ..., "description": tool.description, "example": tool.example}`, where `params` is built from `tool.visible_params` (`name`, `type`, `required`, `default`, `description`, `example` per param) and `return_type` is `"str | (int, str, str)"` when `tool.exec` is set, else `tool.return_type or "unknown"`.
- [x] 1.3 Add `@mcp.custom_route`-style handler `tools(request: Request) -> Response` (registered via the existing `ROUTES`/`register_routes` mechanism, not a decorator, matching `healthz`/`readyz`/`whoami`):
  - Resolve `user` via `_extract_api_key(request)` + `get_user_by_key(raw_key)` (no `groups=` restriction) if a key is present, else `user = None`. Do not 401 on a missing/invalid key.
  - Compute the accessible tool list from 1.1.
  - Branch on `request.query_params.get("format", "json")`:
    - `"json"` (or unrecognized) → `JSONResponse([serialize(t) for t in tools])` using 1.2.
    - `"md"` → `PlainTextResponse("\n\n".join(t.signature for t in tools))`.
    - `"html"` → render the same joined markdown string via `markdown_it.MarkdownIt().render(...)` and return `HTMLResponse(...)`.
- [x] 1.4 Add `("/tools", ["GET"], tools)` to the `ROUTES` list in `mcc/routes.py`.
- [x] 1.5 Import `MarkdownIt` from `markdown_it` and Starlette's `PlainTextResponse`/`HTMLResponse` in `mcc/routes.py`.

## 2. Tests

- [x] 2.1 Test: `GET /tools` with no API key returns `200` and only tools where `groups` is empty or contains `"public"`.
- [x] 2.2 Test: `GET /tools` with a valid key belonging to a user with group/tool grants returns those additional tools too (mirror the fixture pattern used in `tests/test_keys.py::TestKeyIntegration`).
- [x] 2.3 Test: default format (no `format` param) and `?format=json` both return a JSON array; each object has exactly the documented fields and none of the internal execution fields (`fn`, `exec`, `curl`, `python`, `cwd`, `env`, `env_file`, `env_passthrough`, `limits`, `transform`).
- [x] 2.4 Test: an `exec`-type tool's JSON `return_type` is always `"str | (int, str, str)"`, regardless of its declared `return_type` in the fixture YAML.
- [x] 2.5 Test: `?format=md` returns `Content-Type: text/plain` and a body containing each accessible tool's markdown signature block.
- [x] 2.6 Test: `?format=html` returns `Content-Type: text/html` and a body containing HTML-rendered output (e.g. assert an expected tag like `<h2>` or `<code>` appears, not just that it differs from the markdown).
- [x] 2.7 Test: `?format=xml` (or any unrecognized value) returns the same JSON body as the default.

## 3. Verification

- [x] 3.1 Run `uv run pytest tests/`, `uv run ruff check .`, `uv run pyright`, `uv run bandit -c pyproject.toml -r .` — confirm no new violations beyond pre-existing repo debt.
- [x] 3.2 Manually verify via `curl localhost:<port>/tools`, `curl localhost:<port>/tools?format=md`, and opening `http://localhost:<port>/tools?format=html` in a browser. Verified against a live `mcc mcp serve --transport http` instance: `/tools` → 200, `application/json`; `?format=md` → 200, `text/plain`; `?format=html` → 200, `text/html` with well-formed escaped markup; `?format=xml` → falls back to the JSON body. (Browser-open step done via curl'd headers/body inspection rather than an actual browser window, since this agent has no browser access — output confirmed well-formed HTML a browser would render correctly.)
