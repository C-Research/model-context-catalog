## Context

MCC exposes its tool catalog over MCP and over a small set of plain HTTP routes (`mcc/routes.py`): `GET/POST /tools{,/{key}}`, `GET /search`, `GET /whoami`, plus health/metrics/admin routes. There is no visual client today. This change adds one: a small static SPA, served by MCC itself, that only ever talks to routes that already exist.

The defining constraint, arrived at through discussion, is **slimness**: no CORS, no configurable server URL, no client-side router, no new pip extra, no Docker changes, no new backend endpoints, no admin UI. The app is one HTML entry point serving one client-visible surface that toggles between two states (catalog/search, and tool-detail/call) in local component state.

## Goals / Non-Goals

**Goals:**
- Let someone open a browser, hit `/ui`, browse/search the catalog, and call a tool — anonymously or with an API key — using only the existing HTTP API.
- Ship the built assets in the wheel unconditionally, but keep serving off by default (`ui_enabled: false`), matching the existing `contrib` opt-in pattern already documented in this project's CLAUDE.md.
- Keep the feature additive: zero changes to existing route contracts, auth backends, or the MCP tool surface.

**Non-Goals:**
- Admin UI (user/key management) — blocked on read-write admin HTTP routes that don't exist yet.
- Cross-origin deployment (e.g. serving the SPA from GitHub Pages against a separately-hosted API) — same-origin only, so no CORS middleware is added.
- A configurable "server URL" — the SPA always calls its own origin.
- Client-side routing / deep-linkable tool URLs — one entry point, one mounted route.
- Docker/image packaging of the built assets — explicitly deferred; whoever builds an image is responsible for running the build step themselves if they want `/ui` populated.
- Per-return-type result rendering — tool output is plain text, rendered verbatim.

## Decisions

**Settings-gated bundled asset, not a pip extra.** `mcc[ui]` was considered and rejected: pip extras only gate dependency installation, not which files land in a wheel — the same wheel ships to everyone regardless of extras, so an extra would give no real size benefit, only the appearance of one. The built SPA is a few hundred KB of static HTML/CSS/JS with no runtime Python dependency. Bundle it unconditionally via `package-data`, gate *serving* it with a settings flag — this is exactly the `contrib: true` pattern already established for optional built-in tools.

**Source (`ui/`) vs. dist (`mcc/static/ui/`) are separate, and dist is gitignored.** Matches the existing precedent for `site/` (docs build output, already gitignored) and `toolsets/site` (moved into `site/toolsets` at build time, per the `Makefile`'s `docs` target). `ui/` is a normal committed frontend project; `mcc/static/ui/` only exists after `make ui` runs and is never committed. Consequence: anything that packages or runs MCC from a raw checkout (PyPI release, local dev, a hypothetical Docker build) has nothing at `/ui` unless `make ui` ran first in that pipeline. Only the PyPI release path (`publish.yaml`) is wired up as part of this change; Docker and local dev are documented but not automated.

**Static route degrades, never crashes startup.** If `ui_enabled: true` but `mcc/static/ui/index.html` is missing (dist never built), the route logs a warning and responds `404` — same posture as `readyz`'s "degrade, don't crash" behavior for backend checks. A misconfigured or stale deployment loses the UI, not the whole server.

**One route, registered unconditionally, gated inside the handler.** Rather than a separate index route plus an assets route (or conditionally registering routes at import time based on the setting), a single `@route("/ui{path:path}")` — registered exactly like every other route in `mcc/routes.py` — handles everything: it checks `settings.ui_enabled` first, then resolves the requested sub-path (defaulting the empty/`"/"` case to `index.html`) against `mcc/static/ui/`, containment-checking to block traversal. This is simpler than the two-route, import-time-conditional version first built, at the cost of one subtlety: `{path:path}`'s regex is greedy with no separator, so `/uifoo` would otherwise match too (`path="foo"`) — the handler explicitly rejects a non-empty path that doesn't start with `/`.

**No SPA-fallback routing needed.** Because there's deliberately no client-side router, the route only ever needs to serve `index.html` at `/ui`/`/ui/` and the handful of built asset files (`/ui/assets/...`) referenced by it — not a catch-all that serves `index.html` for arbitrary unmatched sub-paths. This is a direct simplification unlocked by the "one entry point, one route" decision.

**Auth is a single localStorage-persisted API key, nothing more.** No server-URL field (same-origin, decided above), no session/cookie mechanism — the SPA is a thin client over the existing `X-API-Key` header contract `_extract_api_key` already supports. `GET /whoami` both validates the key and supplies the identity chip's content; a 401 clears the stored key rather than persisting a known-bad one.

**Frontend stack matches the parent Atlas repo's convention**: React 19 + TypeScript + Vite + pnpm. `api.ts` centralizes every fetch call (parent convention: "All API calls go through `api.ts`"); an `AuthContext` (context + provider + `useAuth()` hook) mirrors the `DatabaseContext` shape, holding the API key and resolved `whoami` info. Since there's no router, there's no `selectedDatabase`-style gate — the equivalent gate is "identity resolution + initial tool list have both settled" before rendering the catalog.

**Tool-call form generation is driven entirely by `GET /tools/{key}`'s existing `params[]` shape** (`name`, `type`, `required`, `default`, `description`, `example` — already returned by `_serialize_tool`). `str`/`int`/`float`/`bool` map to native inputs; `list`/`dict` map to a JSON-validated textarea (client-side `JSON.parse` before submit, blocking on failure) since there's no richer structured-input widget in scope. No new server-side param metadata is needed.

**Result rendering is plain text, full stop.** `POST /tools/{key}` already returns plain text (success or error body) per `http-api.md`; the SPA renders it verbatim in a monospace panel. No attempt to parse/pretty-print based on the tool's declared `return_type`.

**Visual design reuses `docs/stylesheets/orange.css` verbatim** rather than reinventing the palette in a second file that could drift from the docs site's. It's copied into `ui/src/styles/orange.css` with a comment marking it as a manually-synced copy of the canonical file (also published at the docs site's `stylesheets/orange.css`). Only two things from it are actually consumed: its `--md-*` custom properties (every color in `ui/src/styles/app.css` is `var(--md-*)`, not a new hex value) and the couple of selectors that map onto this app's own markup (`.md-header`, `.md-typeset a`/`code`) — everything else in the file (nav, footer, search-result, table selectors) is inert here since there's no matching markup, which is fine; it's not worth stripping. Since this app has none of Material for MkDocs' core CSS/JS, the file's `[data-md-color-scheme="default"|"slate"]` gating needs something to actually set that attribute — a `ThemeContext` (mirroring the `AuthContext`/`DatabaseContext` shape) does that: it sets `data-md-color-scheme` on `<html>`, seeded from `prefers-color-scheme` and persisted in `localStorage`, with a header toggle button. Icons are Font Awesome (`@fortawesome/fontawesome-free`, `fontawesome.min.css` + `solid.min.css` only — no `regular`/`brands`, kept to plain `<i className="fa-solid fa-...">` markup rather than the heavier `react-fontawesome` component wrapper).

## Risks / Trade-offs

- **Wheel built without `make ui` first ships with an empty `/ui`.** → Mitigated for the PyPI path by ordering `publish.yaml`'s node build step before `uv build`. Local dev and any future Docker/CI consumer must remember to run `make ui` themselves; this is a known, accepted gap (Docker explicitly out of scope).
- **No deep-linkable tool URLs.** → Accepted trade-off for bundle/complexity slimness; a user can't share a link straight to a specific tool's call form. Revisit if usage shows this matters.
- **`list`/`dict` params via raw JSON textarea are unforgiving.** → Client-side `JSON.parse` validation catches syntax errors before the request is even sent; the server's existing `ValidationError` → 400 handling remains the backstop for semantically-wrong-but-valid JSON.
- **404 masking (`_lookup_accessible_tool`) is invisible to the UI by design** (unknown vs. inaccessible tool keys are indistinguishable, intentionally, to prevent enumeration). → The SPA must render both cases identically ("not found") and must not try to infer which one happened.
- **Anonymous scoping is entirely server-driven.** → The UI adds no authorization logic of its own; it only ever renders what `GET /tools`/`GET /search` already scoped to the caller. This is a feature, not a gap, but worth stating: the UI cannot "show more" than the API already permits.

## Migration Plan

Purely additive, no data migration:
1. Add `ui_enabled: false` to `mcc/settings.yaml` defaults — no behavior change for existing deployments.
2. Add the static route (inert while `ui_enabled` is false or assets are absent).
3. Scaffold `ui/`, wire `make ui` + `package-data`.
4. Wire the `publish.yaml` node-build step ahead of `uv build`.
5. Opt-in deployments flip `ui_enabled: true` and ensure `mcc/static/ui/` is present (via the built wheel).

Rollback is trivial: set `ui_enabled: false` (or don't build/ship the assets) — no stored state to unwind, since the feature is stateless static content plus calls to already-existing, unchanged routes.

## Open Questions

- Where (if anywhere) should Docker/image-build tooling eventually pick up `make ui`? Explicitly deferred — not blocking this change.
- Should `docs/http-api.md` gain a short pointer to `/ui` for discoverability, given it documents every other route in `routes.py`? Leaning yes, but it's a docs nit, not a design decision — leave to task-time judgment.
