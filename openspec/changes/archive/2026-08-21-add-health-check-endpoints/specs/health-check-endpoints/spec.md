## ADDED Requirements

### Requirement: Liveness endpoint
The server SHALL expose an unauthenticated `GET /healthz` HTTP route that returns `200` with `{"status": "ok"}` whenever the process is able to handle the request. It SHALL NOT contact the search backend, the cache backend, or any other external dependency.

#### Scenario: Process is up
- **WHEN** a `GET /healthz` request arrives
- **THEN** the server responds `200 {"status": "ok"}` without making any backend calls

### Requirement: Readiness endpoint
The server SHALL expose an unauthenticated `GET /readyz` HTTP route that checks connectivity to the search backend and the cache backend, and confirms the tool loader (`mcc.loader.loader`) has at least one registered tool, each check bounded by a short timeout. It SHALL respond `200 {"status": "ok"}` only if all checks succeed, and `503 {"status": "degraded"}` if any check fails or times out. The specific failure SHALL be logged server-side and SHALL NOT appear in the response body.

#### Scenario: All checks pass
- **WHEN** a `GET /readyz` request arrives and the search backend ping, the cache ping, and the tool loader check all succeed within the timeout
- **THEN** the server responds `200 {"status": "ok"}`

#### Scenario: Search backend unreachable
- **WHEN** the search backend ping raises an exception or exceeds the timeout
- **THEN** the server responds `503 {"status": "degraded"}` and logs the failure server-side without including it in the response body

#### Scenario: Cache backend unreachable
- **WHEN** the cache ping raises an exception or exceeds the timeout
- **THEN** the server responds `503 {"status": "degraded"}` and logs the failure server-side without including it in the response body

#### Scenario: Tool loader has no registered tools
- **WHEN** `mcc.loader.loader` has no tools registered
- **THEN** the server responds `503 {"status": "degraded"}` and logs the failure server-side without including it in the response body

### Requirement: Health endpoints are unauthenticated
Both `/healthz` and `/readyz` SHALL be reachable without any MCP authentication credentials (no bearer token, no API key). They SHALL NOT be gated by the server's configured auth backend.

#### Scenario: No credentials required
- **WHEN** either endpoint is called with no `Authorization` header and no API key
- **THEN** the server responds normally (per the scenarios above) rather than rejecting the request for lack of authentication

### Requirement: Health endpoints do not warm the embedding model
Neither `/healthz` nor `/readyz` SHALL trigger loading of the embedding model used by `search()` and tool indexing. Readiness reflects backend connectivity only.

#### Scenario: Readiness check does not load the embedding model
- **WHEN** a `GET /readyz` request is handled
- **THEN** the embedding model is not loaded or invoked as part of handling that request
