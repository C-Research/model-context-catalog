## MODIFIED Requirements

### Requirement: Execute tool by key
The `execute` tool SHALL look up a tool by key and call it with the provided parameters. Auth resolution and logging SHALL be handled by middleware, not inline in the handler. The handler SHALL still check `tool.allows(user)` using the user resolved by middleware, and return "Unauthorized" if access is denied. Before calling the tool, the handler SHALL attempt to elicit any missing required primitive parameters from the client.

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
