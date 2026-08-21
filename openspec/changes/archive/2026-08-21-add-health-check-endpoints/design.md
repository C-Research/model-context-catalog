## Context

FastMCP exposes `@mcp.custom_route(path, methods=[...])` (`fastmcp/server/mixins/transport.py`) to register a plain Starlette-style HTTP route (`(Request) -> Response`) alongside the MCP transport endpoint, on the same ASGI app `mcp.http_app(...)` builds (`mcc/cli/mcp.py`). Nothing in MCC uses this seam today.

MCC already has, unused for this purpose, exactly the connectivity checks a readiness probe needs:
- `mcc/db/es.py`'s `_ESIndexBase.__aenter__` (and the OpenSearch equivalent in `mcc/db/os.py`) already calls `await self._client.info()` when `ping_on_enter = True`, which every concrete `ESIndex`/`_OSIndexBase` subclass (`UsersIndex`, `KeysIndex`, `ToolIndex`) sets. `mcc/db/__init__.py` already dispatches these to the configured backend (`settings.SEARCH_BACKEND`).
- `mcc/cache.py`'s module-level `cache` object (cashews) exposes `await cache.ping()` directly.

## Goals / Non-Goals

**Goals:**
- Give orchestrators (Kubernetes, load balancers, `docker healthcheck`) a way to distinguish "process alive" from "can actually serve `search()`/`execute()`."
- Reuse existing connectivity primitives rather than duplicating client construction.
- Keep both routes unauthenticated, matching how probes and load balancers actually call them.

**Non-Goals:**
- Warming or verifying the lazily-loaded embedding model (`mcc/db/base.py`'s `_get_model()`/`embed()`). A pod can report ready and still take time loading the model on its first real `search()`/tool-indexing call — accepted as a separate, unaddressed concern.
- Anything for the `stdio` transport — these routes only exist on the HTTP-family transports (`http`, `streamable-http`, `sse`) built via `mcp.http_app(...)`; `stdio` has no HTTP surface, so there's nothing to gate or branch on.
- A settings flag to enable/disable these routes. They're inert additions with no effect on existing MCP tool calls or auth, so they're always registered.

## Decisions

**Reuse ping-on-enter and `cache.ping()` directly, no new abstraction.** `/readyz`'s search-backend check is `async with UsersIndex() as _: pass` — entering any concrete `Index` subclass already pings the cluster (`client.info()`) via `ping_on_enter = True`. All concrete indexes hit the same cluster URL (`_client_kwargs()`), so pinging one confirms cluster reachability for all; there's no need to ping `UsersIndex`, `KeysIndex`, and `ToolIndex` separately. A bespoke `_check_search_backend()` (as sketched in the original future-features.md draft) would just reimplement client construction that `mcc/db/es.py`/`mcc/db/os.py` already do correctly.

**Explicit timeout around both checks.** Wrap each check in `asyncio.wait_for(..., timeout=3)`. The underlying `AsyncElasticsearch`/`AsyncOpenSearch` client's own default request timeout isn't guaranteed short enough for a probe endpoint — a hung backend should fail the probe quickly, not hold the connection open indefinitely and risk the orchestrator's own probe timeout doing something less graceful.

**Broad exception handling, narrow response body.** Catch `Exception` broadly around both checks — the point of `/readyz` is "can this pod serve traffic," not diagnosing which backend failed from the HTTP response. The actual exception is logged via `logger.warning` (with the backend name) for operator visibility in log aggregation; the response body only ever says `{"status": "degraded"}`, `503`.

**Unauthenticated by design.** `custom_route`-registered routes are appended to `FastMCP._additional_http_routes` as plain Starlette routes — they sit alongside, not behind, the MCP-auth provider (`get_provider()` in `mcc/auth/backend.py`), which only guards the MCP transport endpoint itself. This is the correct behavior, not a gap: Kubernetes probes and load balancer health checks don't carry MCP bearer tokens or API keys, and health/readiness state is not sensitive information worth gating.

**`/healthz` has zero backend dependency.** It answers "is the process able to handle an HTTP request at all" — deliberately weaker than `/readyz`, and deliberately never fails due to ES/cache issues, so it can't be used by mistake as a proxy for readiness.

## Risks / Trade-offs

- **Probe interval cost** → `/readyz` does a real round-trip to the search backend and cache on every call. If an orchestrator polls aggressively (sub-second intervals), this adds constant background load to both backends. Mitigation: this is inherent to any real readiness check; operators control the probe interval, and a 3s timeout bounds the worst case per call.
- **Single-index ping doesn't catch index-specific failures** → pinging via `UsersIndex` confirms cluster reachability, not that every specific index/mapping is healthy (e.g. a corrupted `mcc-tools` index would still report `ok`). Accepted: this endpoint answers "is the backend reachable," not "is every index correct" — the latter is a different, more expensive check not in scope here.
- **No distinction in the response between "search backend down" vs "cache down"** → an operator debugging a `503` needs to check server logs, not the HTTP response, to know which backend failed. Accepted trade-off for not leaking internal topology to an unauthenticated endpoint.

## Migration Plan

Purely additive, always-on, no settings change. No rollback concerns beyond removing the two route definitions if ever needed — no state, no schema, nothing persisted.
