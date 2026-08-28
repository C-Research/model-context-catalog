## MODIFIED Requirements

### Requirement: Execute tool by key
The `execute` tool SHALL look up a tool by key and call it with the provided parameters. The handler SHALL still check `tool.allows(user)` using the resolved user, and return "Unauthorized" if access is denied. Before its cache lookup, the handler SHALL explicitly check the rate limit for the resolved tool key (per the `mcp-middleware` capability's rate-limit requirement) and, if exceeded, log the rejection and return without invoking the tool. Logging and metrics for a call that does invoke the tool are handled by a hook fired from `ToolModel.call()`, not inline in this handler and not by a separate middleware. Before calling the tool, the handler SHALL attempt to elicit any missing required primitive parameters from the client.

#### Scenario: Successful execution
- **WHEN** a user calls execute with a valid tool key and params
- **THEN** the tool is executed and the result is returned

#### Scenario: Unknown tool
- **WHEN** a user calls execute with an unknown tool key
- **THEN** the handler returns "Unknown tool: {name}"

#### Scenario: Unauthorized
- **WHEN** a user without access calls execute on a restricted tool
- **THEN** the handler returns "Unauthorized"

#### Scenario: Validation error
- **WHEN** params fail the tool's parameter validation after elicitation is skipped or unsupported
- **THEN** the handler returns a validation error message

#### Scenario: Rate limit checked before cache lookup
- **WHEN** rate limiting is enabled and a call's resolved tool key is at its limit
- **THEN** the handler logs the rejection and returns a throttled response without consulting the cache or invoking the tool
