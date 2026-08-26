## Why

MCP clients already discover tools via `search()`/`describe_tools()`, but reaching the catalog requires an MCP client or a shell (`mcc tool list`). The custom HTTP route surface added for `/healthz`, `/readyz`, and `/whoami` makes a curl-able, browser-viewable tool listing straightforward to add now, and it's a natural companion to `/whoami` — both are read-only, keyed off the same API-key identity, and both should report a consistent view of "what can this caller see and do."

## What Changes

- Add `GET /tools` to `mcc/routes.py`, registered via the existing `register_routes(mcp)` mechanism.
- Auth is optional, not required: a missing/invalid API key resolves to `user=None`, which (via the existing `tool.allows(user)` check) surfaces only public-tagged tools — the same anonymous behavior `search()`/`describe_tools()` already have. A valid key (checked via the existing `get_user_by_key`, any group — no `require_admin` gating) widens the result to that user's full accessible set.
- Three response modes via `?format=`:
  - `?format=json` (default): a JSON array, one object per accessible tool, with fields `key`, `groups`, `params` (`name`, `type`, `required`, `default`, `description`, `example`), `return_type`, `description`, `example`.
  - `?format=md`: `text/plain`, the same markdown tool-signature blocks `search()`/`describe_tools()` already build via `tool.signature`, joined for the accessible tool set.
  - `?format=html`: `text/html`, that same markdown rendered via `markdown-it-py` (`MarkdownIt().render(...)`) so the listing is readable directly in a browser tab.
- Extract a shared tool-listing helper (mirroring the existing `whoami_info` pattern: one function, two renderers) so the JSON/markdown views stay in sync with each other and with what `search()`/`describe_tools()` already expose.

## Capabilities

### New Capabilities
- `tools-http-endpoint`: an unauthenticated-by-default, API-key-widened HTTP endpoint (`GET /tools`) that lists the caller's accessible tools in JSON, markdown, or HTML.

### Modified Capabilities
(none — this does not change `search()`, `describe_tools()`, or any existing spec's requirements; it exposes the same underlying access-filtered tool set through a new surface)

## Impact

- **Code**: `mcc/routes.py` (new route + `?format=` handling), likely a new shared helper (parallel to `whoami_info` in `mcc/auth/util.py`, or colocated in `mcc/routes.py` if it doesn't need to be shared with an MCP tool — no existing MCP tool needs this exact JSON shape).
- **Dependencies**: none new — `markdown-it-py` is already a transitive runtime dependency via `rich-click` → `rich` (core `[project.dependencies]`, not dev-only).
- **Auth surface**: no change to the existing API-key mechanism (`get_user_by_key`, `_extract_api_key`, `X-API-Key`/`Bearer` support) — this change is a consumer of it, not a modification to it.
