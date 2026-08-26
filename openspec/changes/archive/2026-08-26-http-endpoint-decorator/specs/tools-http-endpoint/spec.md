## ADDED Requirements

### Requirement: Single tool detail endpoint
The server SHALL expose a `GET /tools/{key}` HTTP route (`@route(optional=True)`) that returns the same serialized shape as one entry of `GET /tools`'s JSON array for the tool identified by `key`. It SHALL respond `404` if `key` does not match any registered tool, or if it does but `tool.allows(request.user)` is `False` — the two cases SHALL be indistinguishable in the response.

#### Scenario: Unknown key
- **WHEN** a `GET /tools/{key}` request arrives with a `key` that matches no registered tool
- **THEN** the server responds `404`

#### Scenario: Known key, inaccessible to caller
- **WHEN** a `GET /tools/{key}` request arrives with a `key` matching a registered tool for which `tool.allows(request.user)` is `False`
- **THEN** the server responds `404`, identical in shape to the unknown-key case

#### Scenario: Known key, accessible to caller
- **WHEN** a `GET /tools/{key}` request arrives with a `key` matching a tool the caller can access
- **THEN** the server responds `200` with that tool's serialized detail

### Requirement: Tool execution over REST
The server SHALL expose a `POST /tools/{key}` HTTP route (`@route(optional=True)`) that executes the tool identified by `key` with the JSON request body as its parameters, and returns the tool's result as plain text. It SHALL apply the same `404` masking as the detail endpoint for an unknown or inaccessible key. It SHALL run the tool with an identity-only context (no stored session state, no write-back).

#### Scenario: Unknown or inaccessible key
- **WHEN** a `POST /tools/{key}` request arrives with a `key` that is unknown or inaccessible to the caller
- **THEN** the server responds `404`, identical to the `GET /tools/{key}` case

#### Scenario: Successful execution
- **WHEN** a `POST /tools/{key}` request arrives with a valid JSON body matching the tool's parameters, for a tool the caller can access
- **THEN** the server responds `200` with the tool's result rendered as plain text

#### Scenario: Validation error
- **WHEN** a `POST /tools/{key}` request body fails the tool's parameter validation
- **THEN** the server responds with an error status and a plain-text body: the full traceback if `settings.DEBUG` is `true`, otherwise a one-line error message

### Requirement: REST tool execution shares its rate-limit bucket with MCP execute
A `POST /tools/{key}` call SHALL be subject to the same rate-limit bucket (`ratelimit:{username-or-anon}:{tool_key}`) as an MCP `execute` call for the same tool key, when rate limiting is enabled.

#### Scenario: Shared bucket across transports
- **WHEN** a user calls a tool via `POST /tools/{key}` and then via the MCP `execute` tool for the same key, within the same rate-limit window
- **THEN** both calls count against the same bucket, and the combined count is checked against the resolved limit

#### Scenario: Throttled REST call
- **WHEN** a `POST /tools/{key}` call would exceed the resolved limit for its bucket
- **THEN** the server does not execute the tool and responds indicating the call was throttled
