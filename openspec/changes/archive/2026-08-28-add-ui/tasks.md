## 1. Settings and static route

- [x] 1.1 Add flat `ui_enabled: false` to `mcc/settings.yaml` defaults
- [x] 1.2 In `mcc/routes.py`, register a single `GET /ui{path:path}` route (always registered, matching every other route) that serves `mcc/static/ui/index.html` at `/ui`/`/ui/` and built assets under `/ui/assets/...`, gated inside the handler on `settings.ui_enabled` and on `mcc/static/ui/index.html` existing on disk
- [x] 1.3 When `ui_enabled` is true but `mcc/static/ui/index.html` is missing, log a warning and respond `404` (no startup failure)
- [x] 1.4 Ensure unmatched `/ui/*` sub-paths (not a real built asset) return `404` — no `index.html` fallback; also reject a bare `/uifoo`-style path that lacks the `/` separator

## 2. UI scaffold (`ui/`)

- [x] 2.1 Scaffold a Vite + React 19 + TypeScript project at `ui/` (pnpm), with `vite.config.ts` `base: "/ui/"`
- [x] 2.2 Add `ui/src/api.ts` with `listTools()`, `getTool(key)`, `callTool(key, params)`, `searchTools(q, minScore)`, `whoami()` — each attaching `X-API-Key` from `localStorage` when present, all requests relative to same origin
- [x] 2.3 Add `ui/src/context/AuthContext.tsx` (context + provider + `useAuth()` hook): holds API key + resolved `whoami` info, persists key to `localStorage`, clears it on a `401` from `GET /whoami`
- [x] 2.4 Add `IdentityBadge` component: shows anonymous vs. authenticated (username + groups), with a key entry/clear control
- [x] 2.5 Add `ToolSearch` + `ToolList` components: query box wired to `GET /search`, falling back to `GET /tools` when empty; render key, groups, description, score. Re-fetch on sign-in/sign-out (accessible tool set depends on the API key)
- [x] 2.5a Add `GroupFilter`: client-side filter by group, chip-toggle multi-select, options derived from the full accessible tool list (independent of the search query), reset when the accessible tool set changes
- [x] 2.6 Add `ToolDetail` + `ToolCallForm` components: fetch `GET /tools/{key}`, render one input per param (`str`/`int`/`float`/`bool` native inputs; `list`/`dict` JSON textarea with client-side `JSON.parse` validation blocking submit on failure)
- [x] 2.7 Add `ToolResult` component: renders `POST /tools/{key}` response body verbatim (success or error) in a monospace panel, including status code on error
- [x] 2.8 Wire `App.tsx` to toggle between catalog view and tool-detail view via local state — no router library
- [x] 2.9 Copy `docs/stylesheets/orange.css` verbatim into `ui/src/styles/orange.css` (canonical palette, not reinvented) and write `ui/src/styles/app.css` for the SPA's own component styling, deriving every color from its `--md-*` custom properties
- [x] 2.10 Add `ThemeContext` (context + provider + `useTheme()` hook) that sets `[data-md-color-scheme]` on `<html>` to `"default"`/`"slate"`, seeded from `prefers-color-scheme` and persisted in `localStorage`, plus a header `ThemeToggle` button — light and dark mode both supported, not just system-driven dark
- [x] 2.11 Add Font Awesome (`@fortawesome/fontawesome-free`, solid style) and use it for the header toggle (sun/moon), catalog title, search input, API key field, sign-out, and back-to-catalog icons

## 3. Build tooling and packaging

- [x] 3.1 Add a `ui` target to the `Makefile`: runs the pnpm build in `ui/` and copies its output into `mcc/static/ui/`
- [x] 3.2 Add `mcc/static/ui/**` to `[tool.setuptools.package-data]` in `pyproject.toml`
- [x] 3.3 Add `mcc/static/ui/` to `.gitignore` (build output, not committed — matches `/site`)

## 4. CI

- [x] 4.1 In `.github/workflows/publish.yaml`, add a Node/pnpm setup + `make ui` step before `uv build`, so the published wheel includes the built assets

## 5. Verification

- [x] 5.1 `cd api/model-context-catalog && uv run pytest`, `uv run pyright`, `uv run ruff check .`, `uv run bandit -c pyproject.toml -r .` all pass
- [x] 5.2 Manually verify: `ui_enabled=false` (default) → `/ui` 404s; `ui_enabled=true` without `make ui` → server starts, warning logged, `/ui` 404s; `ui_enabled=true` after `make ui` → `/ui`, `/ui/`, and `/ui/assets/*` 200, unmatched sub-paths and `/uifoo`-style and encoded-traversal paths 404, anonymous browse/search/call works end to end
