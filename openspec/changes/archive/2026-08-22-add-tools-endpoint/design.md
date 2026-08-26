## Context

`mcc/routes.py` holds every custom HTTP route registered onto the FastMCP `mcp` instance, via a functional `register_routes(mcp)` call from `mcc/app.py` (kept functional rather than decorator-based specifically to avoid a circular import — `app.py` owns `mcp`, `routes.py` needs to register onto it without importing back from `app.py`).

Auth on this HTTP surface is deliberately independent of `settings.auth`/`get_provider()` (the OAuth-proxy/JWT/dev backend that gates MCP protocol tool calls). That backend authenticates fine for MCP clients like Claude Desktop, but a Bearer token issued to an MCP client is not retrievable from a plain browser tab — there's no cookie session to fall back on. So every custom route instead resolves identity straight from the `mcc-keys` index:

- `_extract_api_key(request)` pulls the raw key from `X-API-Key` (checked first) or `Authorization: Bearer <key>`.
- `get_user_by_key(raw_key, groups=None)` (in `mcc/auth/util.py`) resolves that key to a `UserModel`, optionally restricted to a group list (`require_admin` passes `groups=["admin"]`; nothing else does today).
- `whoami_info(user)` is the existing precedent for sharing a computation between an MCP tool (`whoami()` in `app.py`, renders text) and an HTTP route (`whoami` in `routes.py`, renders JSON).

Separately, tool-access filtering already exists and is reused everywhere: `tool.allows(user)` → `mcc.auth.can_access(user, tool)`. Passing `user=None` already does the right thing for an anonymous caller — it returns `True` only for tools with no `groups` or `"public"` in `groups`. `search()`/`describe_tools()` in `app.py` already rely on this to serve anonymous MCP callers.

The "detailed view" of a tool already has a defined shape, expressed as markdown by `mcc/templates/tool_signature.md` (via `ToolModel.signature`) and `param_signature.md`:
- Header line: `key`, a parenthesized param list (`name:type` or `name:type="default"`), `-> return_type` — except `exec`-type tools, which always render `str | (int, str, str)` instead of `tool.return_type` (an exec tool's actual runtime return is a `(returncode, stdout, stderr)`-shaped tuple coerced through `_coerce_result`, not whatever free-text `return_type` a YAML author put in the file).
- Per-visible-param description line, only when `param.description` is non-empty.
- `tool.description` and `tool.example`, each only when non-empty.

Internal execution fields (`fn`, `exec`, `curl`, `python`, `cwd`, `env`, `env_file`, `env_passthrough`, `limits`, `transform`) are never in that markdown and must not leak into the new JSON/HTML views either — same boundary, new format.

`markdown-it-py` is already a transitive runtime dependency (`rich-click` → `rich`, both in `[project.dependencies]`), so `MarkdownIt().render(...)` is available with no new dependency. `markdown`/`pymdown-extensions` (pulled in only via `zensical`, a `[dependency-groups] dev` entry) must NOT be used — importing them would work in a dev venv and break a `uv sync --no-dev` production install.

## Goals / Non-Goals

**Goals:**
- Add `GET /tools`, returning the caller's accessible tool set (anonymous → public tools only; valid key → full accessible set) in one of three formats selected by `?format=`.
- Reuse every existing primitive (`_extract_api_key`, `get_user_by_key`, `tool.allows`, `tool.signature`/templates) rather than re-deriving equivalent logic.
- Keep the JSON, markdown, and HTML views built from one shared computation, so they can't drift from each other the way an ad hoc per-format implementation could.

**Non-Goals:**
- No changes to `search()`, `describe_tools()`, or any existing MCP tool.
- No pagination, filtering by group/query, or sorting options beyond the loader's natural key order — this is a full listing endpoint, not a search endpoint (that's what `search()` is for).
- No rate limiting or audit logging for this route — out of scope here; it's a pre-existing gap across the whole custom-route surface (`/healthz`, `/readyz`, `/whoami` have the same gap today), not something this change should fix incidentally.
- No retroactive spec for the existing `/whoami`/`require_admin`/API-key auth work — this change treats that as given context (described above), not something to formalize here.

## Decisions

**Decision: one shared "accessible tools" computation, not per-format duplication.**
Add a helper — `tools_for(user) -> list[ToolModel]` (or return the filtered+sorted list inline) — that does exactly what `search()`/`describe_tools()` already do: `[t for t in loader.values() if t.allows(user)]`, sorted by `t.key`. Each format renderer (JSON serializer, markdown joiner, HTML wrapper) consumes this same list. Placed in `mcc/routes.py` since — unlike `whoami_info` — no existing MCP tool needs this exact structured-JSON shape; `describe_tools()` already has its own simpler markdown-joining loop and doesn't need to be refactored to share code here. If a future MCP tool needs the same JSON shape, promote the helper to `mcc/auth/util.py` or `mcc/models.py` at that point — not preemptively.

**Decision: JSON serialization is a new, explicit dict-builder — not `tool.model_dump()`.**
`ToolModel` carries `fn`/`exec`/`curl`/`python`/`env`/`limits`/etc. `model_dump()` would leak all of them. Build the response dict explicitly, field by field: `key`, `groups` (via `tool.sorted_groups`), `params` (list of `{name, type, required, default, description, example}` from `tool.visible_params`, one dict-comprehension away from `ParamModel.model_dump()` restricted to those fields), `return_type` (`"str | (int, str, str)"` when `tool.exec` else `tool.return_type or "unknown"` — matching the template's exact special-case and fallback), `description`, `example`.

**Decision: `?format=md` and `?format=html` both render from `tool.signature`, not a second markdown builder.**
`tool.signature` already renders the exact markdown block per tool via Jinja. `?format=md` joins those blocks with the same `"\n\n".join(...)` convention `search()`/`describe_tools()` use, returned as `text/plain`. `?format=html` takes that same joined string and passes it through `MarkdownIt().render(...)`, returned as `text/html`. No separate markdown-generation path — the JSON path is the only place field-by-field serialization happens; `md`/`html` are two renderings of the one already-existing markdown block.

**Decision: default format is `json`, not `md`.**
`/healthz`, `/readyz`, `/whoami` are all JSON-first. Consistency across the whole custom-route surface matters more than matching `search()`/`describe_tools()`'s text-first MCP convention — a browser or script hitting a bare `/tools` should get structured data by default; markdown/HTML are opt-in via the query param for the "view in a browser" use case specifically.

**Decision: unknown `?format=` values.**
Fall back to `json` rather than 400ing. Precedent: none of the existing routes validate query params today, and a typo'd `?format=jsn` returning the safe default is friendlier than a hard error for a read-only, side-effect-free endpoint.

## Risks / Trade-offs

- **[Risk] Public-tool listing is now reachable with zero auth, at scale.** Anyone can hit `/tools` with no key and see every public tool's full signature (params, description, example) — previously this required an MCP session (still true for `search()`/`describe_tools()` today, so this isn't a new exposure, just a new transport for the same data). → Mitigation: none needed beyond what already exists; `tool.allows(None)` already gates this identically to the MCP-tool path. If this becomes a concern, it's a `can_access`-level policy change, not something specific to this route.
- **[Risk] `markdown-it-py`'s HTML output is unsanitized user-adjacent content if any tool's `description`/`example`/`param.description` ever contains attacker-influenced markdown.** Tool definitions come from YAML files authored by whoever controls the deployment (not runtime user input), so this is low-risk today — but if tool metadata is ever sourced from something less trusted, `?format=html` would render it unescaped. → Mitigation: none needed now; flag as an open question below in case tool authoring trust model changes.
- **[Risk] No rate limiting.** A public, unauthenticated, potentially-large JSON/HTML response with no throttling is a mild DoS surface. → Mitigation: accepted as a pre-existing gap across the whole custom-route surface (see Non-Goals); not fixed here.

## Open Questions

- If tool metadata (`description`, `example`, `param.description`) ever becomes less trusted than "YAML authored by the deployer," `?format=html` will need explicit sanitization (e.g. `markdown_it.utils.escape_html` on inputs, or an HTML-sanitizing pass on the rendered output). Not needed today; worth a comment at the render call site pointing back here.
- Should the shared "accessible tools" helper eventually be promoted out of `mcc/routes.py` if a future MCP tool wants the same structured JSON shape (e.g. a hypothetical `list_tools_json()` tool)? Deferred until there's a second caller.
