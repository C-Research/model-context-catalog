---
icon: lucide/map
---

# Future Features

Ideas for extending MCC beyond its current MCP tool surface (`search`, `execute`, `describe_tools`, `whoami`, `get_session`/`set_session`). None of these are committed — this is a working list of concrete, code-grounded proposals, ordered roughly by how directly they close an operational gap versus how much new surface area they'd add.

The common thread: MCC is served via `mcp.http_app(transport=...)` (`mcc/cli/mcp.py`), which builds a Starlette ASGI app under the hood — the same seam a bare FastAPI app would give you. FastMCP exposes `@mcp.custom_route(path, methods=[...])` to hang plain HTTP routes off that same app, alongside the MCP transport endpoint. Nothing in the codebase uses `custom_route` today. Several of the ideas below are specifically about using that seam.


## 5. A thin REST admin API mirroring the CLI

**Problem.** Tool and user management exist only as CLI commands (`mcc tool add/list`, `mcc user add/list/remove` — `mcc/cli/tools.py`, `mcc/cli/users.py`). Anyone building a dashboard on top of MCC (including the hosting product's control plane, per `bd/architecture.md` §2.1) currently has to shell out to the CLI or reimplement its logic against `mcc/db.py` directly.

**Design.** A set of `custom_route`s under `/admin/*`, backed by the same functions the CLI commands already call (`mcc/db.py`'s `ToolIndex`/`UsersIndex` wrappers), not a reimplementation:

- `GET /admin/tools`, `POST /admin/tools`, `DELETE /admin/tools/{key}` — mirrors `mcc tool list/add/remove`.
- `GET /admin/users`, `POST /admin/users`, `DELETE /admin/users/{username}` — mirrors `mcc user list/add/remove`.

Gated behind the same auth backends MCC already supports (`mcc/auth/backend.py`) with an admin-group check, not a separate auth mechanism — reuses `current_user_var` and the existing group model rather than inventing new permissions.

**Why it matters now.** This is the seam the hosting dashboard (`bd/architecture.md` §2.1, "Control API ... Dashboard") needs regardless — building it as a documented, reusable route on MCC itself means self-hosted users get an admin API for free, and the hosting product's control plane doesn't need a bespoke integration layer against MCC internals.

**Complexity.** Medium-high relative to the others — this is real API surface (request/response schemas, pagination, error handling) rather than a single endpoint, and it needs careful thought about whether it duplicates or supersedes the CLI long-term.

## 7. A human-facing catalog browser page

**Problem.** The only way to see what's in a catalog today is via an MCP client calling `search`/`describe_tools`, or reading YAML files directly. There's no way for a human (a maintainer auditing a large catalog, or a customer deciding what to enable) to just look at it.

**Design.** A `custom_route` serving a small static page (server-rendered or a minimal SPA) that calls the same underlying logic as `search()`/`describe_tools()` (`mcc/app.py`) over plain JSON, with a search box and a list view — no new business logic, just a UI over existing read paths:

```python
@mcp.custom_route("/catalog", methods=["GET"])
async def catalog_ui(request):
    return HTMLResponse(_render_catalog_page())

@mcp.custom_route("/catalog/api/search", methods=["GET"])
async def catalog_search_api(request):
    query = request.query_params.get("q", "")
    user = ...  # resolve same as MCP tool calls
    results = await loader.search(query)
    return JSONResponse([...])
```

**Why it matters now.** Cheapest, lowest-risk item on this list — no new backend logic, and it's a natural precursor to the hosted dashboard's tool browser (`bd/architecture.md` §2.1) without committing to the dashboard's full design yet.

**Complexity.** Low-medium. Mostly frontend work; backend is a thin JSON wrapper around functions that already exist.


┌─────────────────────────────────────────────────────────────────┐
│  READ-ONLY / OBSERVABILITY          gate: none or /whoami-style │
├─────────────────────────────────────────────────────────────────┤
│  /catalog/status     tool count, load timestamp, source paths   │
│  /cache/stats        wraps existing cache_stats() tool           │
│  /metrics            Prometheus-format counters (calls, errors, │
│                      rate-limit rejections, cache hit ratio)     │
├─────────────────────────────────────────────────────────────────┤
│  READ-ONLY / ADMIN                  gate: require_admin          │
├─────────────────────────────────────────────────────────────────┤
│  /admin/users        list_users() over HTTP, redacted            │
│  /admin/keys         list_keys() over HTTP — prefix/username/    │
│                      expiry only, never hash                     │
│  /admin/tools        loader.list_all() equivalent — full catalog │
│                      signatures, incl. groups per tool            │
├─────────────────────────────────────────────────────────────────┤
│  MUTATING / ADMIN                   gate: require_admin + ???    │
├─────────────────────────────────────────────────────────────────┤
│  POST /admin/reload      loader.reload() — no MCP tool exposes   │
│                          this today; only a CLI restart does     │
│  POST /admin/keys/revoke revoke_key(username) — kill a leaked    │
│                          key from an incident channel, no SSH    │
│  POST /admin/users/{u}/groups   add_group/remove_group           │
└─────────────────────────────────────────────────────────────────┘