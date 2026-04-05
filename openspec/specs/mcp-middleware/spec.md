## ADDED Requirements

### Requirement: Auth middleware resolves user
The server SHALL register an auth middleware that resolves the current user on every MCP request and makes it available to handlers. The middleware SHALL NOT block requests — it only resolves and stashes the user identity.

#### Scenario: Authenticated request
- **WHEN** a request arrives with valid auth credentials
- **THEN** the middleware resolves the user and makes it available for downstream handlers

#### Scenario: Unauthenticated request
- **WHEN** a request arrives without auth credentials
- **THEN** the middleware sets the user to None and allows the request to proceed

### Requirement: Logging middleware
The server SHALL register a logging middleware that logs tool executions with the resolved username, tool key, parameters, and timing.

#### Scenario: Tool execution logged
- **WHEN** a tool is executed via MCP
- **THEN** the middleware logs the username, tool key, and parameters

### Requirement: Timing middleware
The server SHALL register FastMCP's built-in `TimingMiddleware` to capture performance metrics for all MCP operations.

#### Scenario: Timing captured
- **WHEN** any MCP operation completes
- **THEN** the middleware logs the operation type and elapsed time
