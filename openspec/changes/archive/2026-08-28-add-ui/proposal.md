## Why

MCC currently has no visual surface — discovering and calling tools requires an MCP client or raw HTTP calls against the routes in `mcc/routes.py`. A minimal, optional web UI lets someone browse the catalog, search it, and call a tool from a browser, without requiring a new backend capability: `/tools`, `/tools/{key}` (GET/POST), `/search`, and `/whoami` already provide everything a "view and call tools" experience needs.

## What Changes

- Add a new `ui/` source directory: a slim single-page app (React 19 + TypeScript + Vite + pnpm, matching the parent Atlas repo's frontend convention) with exactly one entry point and one client-visible route — no router library. The app toggles between a catalog/search view and a tool-detail/call view via local component state.
- The SPA reads and calls only existing HTTP endpoints: `GET /whoami`, `GET /tools`, `GET /tools/{key}`, `POST /tools/{key}`, `GET /search`. No new API endpoints are added for the UI to consume.
- Add one new server-side static route, `GET /ui{path:path}` (matching `/ui` and every sub-path under it), gated at request time by a new flat `ui_enabled` setting (default `false`, mirroring the existing `contrib` opt-in pattern). Serves the built SPA's `index.html` at `/ui`/`/ui/` and each built asset under `/ui/assets/...`; an unmatched sub-path is a plain `404` (no SPA-fallback — there's no client-side router to hand it to). If `ui_enabled` is `true` but the built assets are missing, the server logs a warning and responds `404` (degrades, does not fail startup) — same posture as `readyz`.
- Auth in the UI is a single "API Key" field: the caller pastes a key, the SPA stores it in `localStorage`, and attaches it as `X-API-Key` on every request. No key means anonymous, scoped to public tools by the existing server-side behavior — the UI adds no new authorization logic.
- Add a `make ui` target (pnpm build in `ui/`, output copied to `mcc/static/ui/`) and a `mcc/static/ui/` package-data entry so the built assets ship in the wheel. `mcc/static/ui/` is build output — gitignored, not committed — so anything consuming a raw checkout (including local dev) must run `make ui` before the route has anything to serve. `publish.yaml` gets a node build step before `uv build` so the published wheel already contains the built assets. Docker/image-build tooling is explicitly out of scope for this change.
- Visual design reuses `docs/stylesheets/orange.css` verbatim (copied into `ui/src/styles/`, same file as the docs site publishes at `stylesheets/orange.css`) rather than reinventing a palette — not a new design language. Supports both light and dark (Material's own `default`/`slate` scheme names), toggled via a `ThemeContext` that sets `[data-md-color-scheme]` on `<html>`, persisted in `localStorage`, defaulting to system preference. Icons use Font Awesome (`@fortawesome/fontawesome-free`, solid style only).
- Admin functionality (`GET /users` and beyond) is explicitly excluded from this UI until read-write admin HTTP routes exist; this change is view-and-call-tools only.

## Capabilities

### New Capabilities
- `web-ui`: an optional, settings-gated static SPA (served at `/ui`) that lets a caller browse/search the tool catalog and execute tools via the existing HTTP API, authenticating optionally via an API key stored client-side.

### Modified Capabilities
_None — no existing route's request/response contract changes. The new `/ui` route is additive and orthogonal to `tools-http-endpoint`, `users-http-endpoint`, etc._

## Impact

- **New code**: `ui/` (SPA source, not packaged), one new static route + settings flag in `mcc/routes.py`/`mcc/settings.yaml`.
- **Build/release**: `Makefile` (`make ui` target), `pyproject.toml` package-data glob for `mcc/static/ui/**`, `.github/workflows/publish.yaml` (node build step before `uv build`).
- **No changes** to existing route handlers, auth backends, or the MCP tool surface.
- **Explicitly out of scope**: admin read-write UI, Docker/image packaging, CORS (same-origin only), any new backend API endpoints.
