## ADDED Requirements

### Requirement: Route decorator declares, registers, and gates a custom HTTP route
The server SHALL provide an `@route(path, methods=None, *, admin=False, anonymous=False, optional=False)` decorator that both registers `path`/`methods` (`methods` defaulting to `["GET"]`) as a custom HTTP route and gates it: it SHALL resolve the caller's identity from an API key and gate the route according to its declared mode. The decorator SHALL attach the resolved user (or `None`) to `request.scope["user"]` before invoking the handler, readable as `request.user`. No separate registration step SHALL be required beyond applying the decorator.

#### Scenario: Decorating a handler registers its route
- **WHEN** a handler is decorated with `@route("/example")`
- **THEN** a `GET /example` route becomes reachable with no further registration call

#### Scenario: Default mode requires a resolved user
- **WHEN** a route decorated with `@route("/example")` (no method/mode kwargs) receives a request with no valid API key
- **THEN** the server responds `401` and the handler is never invoked

#### Scenario: Default mode passes through a resolved user
- **WHEN** a route decorated with `@route("/example")` receives a request with a valid API key
- **THEN** the handler is invoked with `request.user` set to the resolved user

### Requirement: Anonymous mode never attempts key resolution
`@route(anonymous=True)` SHALL NOT attempt to extract or resolve an API key from the request under any circumstance. `request.user` SHALL always be `None` for such a route, regardless of what credentials the request carries.

#### Scenario: Anonymous route ignores a valid key
- **WHEN** a route decorated with `@route(anonymous=True)` receives a request carrying a valid API key
- **THEN** the handler is invoked with `request.user` set to `None`, and no key lookup is performed

### Requirement: Optional mode resolves without requiring
`@route(optional=True)` SHALL attempt to resolve an API key if one is present, setting `request.user` to the resolved user on success. It SHALL NOT respond `401` when no key is present or the key is invalid/expired — `request.user` SHALL be `None` and the handler SHALL still be invoked.

#### Scenario: Optional route with no key
- **WHEN** a route decorated with `@route(optional=True)` receives a request with no API key
- **THEN** the handler is invoked with `request.user` set to `None`, and the response is not `401`

#### Scenario: Optional route with a valid key
- **WHEN** a route decorated with `@route(optional=True)` receives a request with a valid API key
- **THEN** the handler is invoked with `request.user` set to the resolved user

### Requirement: Admin mode requires admin group membership
`@route(admin=True)` SHALL require a resolved user who belongs to the `admin` group. It SHALL respond `401` if no user resolves, and SHALL respond `401` if a user resolves but is not in the `admin` group — the handler SHALL NOT be invoked in either case.

#### Scenario: Admin route with a non-admin user
- **WHEN** a route decorated with `@route(admin=True)` receives a request with a valid API key resolving to a user not in the `admin` group
- **THEN** the server responds `401` and the handler is never invoked

#### Scenario: Admin route with an admin user
- **WHEN** a route decorated with `@route(admin=True)` receives a request with a valid API key resolving to a user in the `admin` group
- **THEN** the handler is invoked with `request.user` set to that user

### Requirement: Contradictory decorator kwargs are rejected at decoration time
`@route(admin=True, anonymous=True)` and `@route(admin=True, optional=True)` SHALL raise an error when the decorator is applied (at import/module-load time), not on a live request.

#### Scenario: admin combined with anonymous
- **WHEN** a handler is decorated with `@route(admin=True, anonymous=True)`
- **THEN** an error is raised immediately, before any request is handled

#### Scenario: admin combined with optional
- **WHEN** a handler is decorated with `@route(admin=True, optional=True)`
- **THEN** an error is raised immediately, before any request is handled

### Requirement: API key extraction checks header, then query parameter
The decorator SHALL extract the raw API key by checking, in order: the `X-API-Key` header, then the `Authorization: Bearer <key>` header, then the `api-key` query parameter. The first present source SHALL be used; a header SHALL always take priority over the query parameter when both are present.

#### Scenario: Header takes priority over query parameter
- **WHEN** a request carries both a valid `X-API-Key` header and a different `?api-key=` query parameter
- **THEN** the server resolves the caller from the header value, not the query parameter

#### Scenario: Query parameter used when no header is present
- **WHEN** a request carries no `X-API-Key` or `Authorization` header but does carry a `?api-key=` query parameter with a valid key
- **THEN** the server resolves the caller from the query parameter value
