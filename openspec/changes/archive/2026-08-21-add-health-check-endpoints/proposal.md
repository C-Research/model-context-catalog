## Why

MCC has no HTTP health check today. Orchestrators (Kubernetes liveness/readiness probes, a load balancer's health check, `docker healthcheck`) have nothing to poll — the only signal available is whether a full MCP handshake succeeds, which conflates "process is up" with "a full MCP session works." This is a prerequisite for running MCC under an orchestrator that needs to detect and restart/pull a broken pod automatically, rather than relying on someone noticing manually.

## What Changes

- Add `/healthz` (liveness) and `/readyz` (readiness) HTTP endpoints via FastMCP's `@mcp.custom_route(...)` — the first use of that seam in the codebase.
- `/healthz` is a pure liveness check: always `200 {"status": "ok"}` if the process can handle the request at all. No backend calls.
- `/readyz` exercises the two backends MCC needs to serve `search()`/`execute()`: the search backend (via the existing ping-on-enter mechanism already in `mcc/db/es.py`/`mcc/db/os.py`) and the cache backend (`cache.ping()` in `mcc/cache.py`). Returns `200 {"status": "ok"}` if both succeed within a short timeout, `503 {"status": "degraded"}` otherwise. The failing backend is logged server-side, not exposed in the response body.
- Both routes are unauthenticated by design — `custom_route`-registered routes bypass FastMCP's MCP-auth provider, matching the reality that orchestrator probes and load balancers don't carry MCP credentials.
- Out of scope: warming or verifying the lazily-loaded embedding model (`mcc/db/base.py`). `/readyz` is connectivity-only.
- Only meaningful for HTTP-family transports (`http`, `streamable-http`, `sse`); inert under `stdio` with no code branching required.

## Capabilities

### New Capabilities

- `health-check-endpoints`: unauthenticated `/healthz` and `/readyz` HTTP routes for liveness/readiness probing.

### Modified Capabilities

(none)

## Impact

- `mcc/app.py` — add the two `@mcp.custom_route` handlers, near the existing `@mcp.tool()`/`@mcp.prompt` definitions.
- No changes to `mcc/settings.yaml`, `mcc/models.py`, `mcc/middleware.py`, or `mcc/db/*.py` — reuses existing ping-on-enter and `cache.ping()` primitives directly.
- No new dependencies.
