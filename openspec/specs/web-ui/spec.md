## ADDED Requirements

### Requirement: Static UI route is settings-gated
The `/ui` route SHALL be registered unconditionally (like every other route), but SHALL respond `404` to every request unless `settings.ui_enabled` is `true`. The setting SHALL default to `false` and SHALL NOT be nested under another key.

#### Scenario: UI disabled by default
- **WHEN** the server starts with default settings (`ui_enabled` unset)
- **THEN** a request to `/ui` receives `404`

#### Scenario: UI enabled with built assets present
- **WHEN** `settings.ui_enabled` is `true` and `mcc/static/ui/index.html` exists on disk
- **THEN** `GET /ui` returns `200` with the built `index.html` as the response body

### Requirement: Missing build output degrades without failing startup
When `ui_enabled` is `true` but the built SPA assets are missing, the server SHALL log a warning and respond `404` rather than fail to start.

#### Scenario: Enabled but never built
- **WHEN** `settings.ui_enabled` is `true` and `mcc/static/ui/index.html` does not exist
- **THEN** the server starts successfully, and a request to `/ui` logs a warning naming the missing path and receives `404`

### Requirement: Mounted route serves the built app and its assets only
The `/ui` route SHALL serve the built `index.html` at `/ui` (and at `/ui/`) and SHALL serve each built static asset referenced by it (e.g. `/ui/assets/<file>`) from `mcc/static/ui/`. It SHALL NOT implement fallback routing for arbitrary unmatched sub-paths, since the SPA has no client-side router, and SHALL NOT match a path that merely starts with `ui` without a `/` separator (e.g. `/uifoo`).

#### Scenario: Load the app shell
- **WHEN** a client sends `GET /ui`
- **THEN** the response is `200`, `Content-Type: text/html`, with the built `index.html` body

#### Scenario: Load a built asset
- **WHEN** a client sends `GET /ui/assets/<hashed-filename>.js` for a file that exists in `mcc/static/ui/assets/`
- **THEN** the response is `200` with that file's contents

#### Scenario: Unknown sub-path
- **WHEN** a client sends `GET /ui/does-not-exist`
- **THEN** the response is `404` (no `index.html` fallback is served)

### Requirement: Light and dark mode are both supported
The SPA SHALL support both a light and a dark color scheme, using the same palette the docs site publishes (`docs/stylesheets/orange.css`, reused verbatim rather than redefined). It SHALL default to the browser's `prefers-color-scheme`, persist an explicit choice in `localStorage`, and provide a control to toggle between them.

#### Scenario: First visit, no stored preference
- **WHEN** the SPA loads with no `localStorage` scheme entry
- **THEN** it renders in the scheme matching the browser's `prefers-color-scheme`

#### Scenario: Toggle persists
- **WHEN** a caller uses the theme toggle control
- **THEN** the SPA switches scheme immediately and persists the choice in `localStorage`, so a later reload uses it instead of `prefers-color-scheme`

### Requirement: SPA calls only pre-existing HTTP endpoints
The bundled SPA SHALL call only `GET /whoami`, `GET /tools`, `GET /tools/{key}`, `POST /tools/{key}`, and `GET /search`. It SHALL NOT depend on any endpoint not already defined in `mcc/routes.py` at the time of this change.

#### Scenario: Anonymous catalog browse
- **WHEN** the SPA loads with no API key stored in `localStorage`
- **THEN** it calls `GET /tools` (or `GET /search` once a query is entered) with no `X-API-Key` header, and renders the returned tool list, which is server-scoped to public tools

### Requirement: Catalog can be filtered by group
The SPA SHALL let a caller filter the currently-shown tool listing by one or more of the groups present across their accessible tools (as returned by `GET /tools`), independent of the search query. Selecting no group SHALL show every result; the filter is client-side only — no new query parameter is sent to the server.

#### Scenario: Filter to one group
- **WHEN** a caller selects a group filter (e.g. `admin`)
- **THEN** the listing shows only results whose `groups` include that group

#### Scenario: Filter options track accessible tools
- **WHEN** the caller's accessible tool set changes (sign-in, sign-out)
- **THEN** the set of selectable group filters updates to match, and any previously-selected group no longer available is cleared

### Requirement: Client-side API key authentication
The SPA SHALL provide a control to set or clear an API key, persist it in `localStorage`, and attach it as the `X-API-Key` header on every subsequent API call. A key that `GET /whoami` rejects SHALL NOT be persisted.

#### Scenario: Set a valid key
- **WHEN** a caller enters an API key and it resolves via `GET /whoami` (`200`)
- **THEN** the SPA persists the key in `localStorage`, attaches it as `X-API-Key` on future requests, and displays the resolved username and groups

#### Scenario: Set an invalid key
- **WHEN** a caller enters an API key and `GET /whoami` responds `401`
- **THEN** the SPA displays an error, does not persist the key, and continues operating as anonymous

#### Scenario: Returning visit with a stored key
- **WHEN** the SPA loads and `localStorage` already contains a previously-validated key
- **THEN** the SPA attaches it as `X-API-Key` on its initial `GET /whoami` and catalog calls without requiring re-entry

#### Scenario: Catalog refreshes on sign-in and sign-out
- **WHEN** a caller sets or clears their API key while the catalog view is showing
- **THEN** the SPA re-fetches `GET /tools` (or `GET /search`, if a query is active) so the listing reflects the newly-scoped set of accessible tools

### Requirement: Tool call form is generated from tool metadata
For a selected tool, the SPA SHALL render one input per parameter returned by `GET /tools/{key}`: `str`/`int`/`float`/`bool` parameters SHALL use native inputs matching their type; `list`/`dict` parameters SHALL use a text area whose contents are parsed as JSON client-side before submission.

#### Scenario: Submit a call with scalar params
- **WHEN** a caller fills in all required `str`/`int`/`float`/`bool` fields and submits
- **THEN** the SPA sends `POST /tools/{key}` with a JSON body mapping each parameter name to its entered value

#### Scenario: Malformed JSON in a list/dict param
- **WHEN** a `list` or `dict` parameter's text area contains text that fails `JSON.parse`
- **THEN** the SPA blocks submission and displays a validation error without sending a request

### Requirement: Tool results render as plain text
The SPA SHALL render the body of every `POST /tools/{key}` response — success or error — verbatim as plain text, with no formatting derived from the tool's declared return type.

#### Scenario: Successful call
- **WHEN** `POST /tools/{key}` responds `200` with a text body
- **THEN** the SPA displays that body verbatim in a monospace output panel

#### Scenario: Error response
- **WHEN** `POST /tools/{key}` responds `400`, `404`, `429`, or `500` with a text body
- **THEN** the SPA displays that body verbatim alongside the status code, without retrying automatically or attempting to distinguish a `404` for an unknown key from one for an inaccessible key
