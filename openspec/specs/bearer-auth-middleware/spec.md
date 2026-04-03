## ADDED Requirements

### Requirement: Bearer token resolved at session init
The system SHALL provide a `BearerAuthMiddleware` subclassing FastMCP's `Middleware`. Its `on_initialize` hook SHALL extract the `Authorization` header from the HTTP request using `get_http_request()`, strip the `Bearer ` prefix, look up the token in the user store, and store the resolved user in session state under the key `"current_user"`. The stored user dict SHALL NOT contain `token_hash`.

#### Scenario: Valid token resolves to user in session state
- **WHEN** a client connects with `Authorization: Bearer <valid_token>`
- **THEN** `ctx.get_state("current_user")` returns the user dict (without token_hash) for all subsequent tool calls in that session

#### Scenario: Invalid token stores None
- **WHEN** a client connects with `Authorization: Bearer <unknown_token>`
- **THEN** `ctx.get_state("current_user")` returns `None`

#### Scenario: Missing Authorization header stores None
- **WHEN** a client connects with no `Authorization` header
- **THEN** `ctx.get_state("current_user")` returns `None`

#### Scenario: Malformed Authorization header stores None
- **WHEN** a client connects with `Authorization: Basic abc123` (non-Bearer scheme)
- **THEN** `ctx.get_state("current_user")` returns `None`

### Requirement: Token never propagated beyond middleware
The bearer token string SHALL only exist within the scope of `on_initialize`. It SHALL NOT be stored in session state, logged, returned in any tool response, or passed to any function other than the user store token lookup.

#### Scenario: Session state contains no token
- **WHEN** a valid bearer token is presented and the session is initialized
- **THEN** `ctx.get_state("current_user")` does not contain any field named `token`, `token_hash`, or similar

### Requirement: Middleware registered on FastMCP app
`BearerAuthMiddleware` SHALL be registered on the FastMCP app instance at startup via `mcp = FastMCP(..., middleware=[BearerAuthMiddleware()])` or `mcp.add_middleware(BearerAuthMiddleware())`.

#### Scenario: Middleware active on app startup
- **WHEN** the MCP server starts
- **THEN** `BearerAuthMiddleware` intercepts `on_initialize` for every new client connection
