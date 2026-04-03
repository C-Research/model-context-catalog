## ADDED Requirements

### Requirement: Execute registered as FastMCP tool in app.py
The `execute` function SHALL be registered on the FastMCP app instance using the `@mcp.tool()` decorator in `mcc/app.py`. It SHALL close over the module-level `loader` singleton from `mcc/loader.py`.

#### Scenario: execute is visible as an MCP tool
- **WHEN** the FastMCP app starts
- **THEN** `execute` is listed as an available MCP tool

### Requirement: Execute only dispatches to catalog tools
The `execute` MCP tool SHALL only call functions present in the `loader` registry. If the requested `name` is not in the registry, it SHALL return an error string to the LLM without raising an exception.

#### Scenario: Unknown tool name returns error string
- **WHEN** execute is called with a name not in the registry
- **THEN** execute returns `"Unknown tool: <name>"`

#### Scenario: Known tool dispatches to registered callable
- **WHEN** execute is called with a valid name and correct params
- **THEN** the registered function is called and its return value is returned

### Requirement: Parameter validation via Pydantic before dispatch
The `execute` tool SHALL validate the provided `params` dict against the tool's pre-built Pydantic model before calling the function. If validation fails, it SHALL return the validation error message to the LLM without raising an exception.

#### Scenario: Missing required parameter returns validation error
- **WHEN** execute is called without a required parameter
- **THEN** execute returns `"Validation error for tool '<name>': <pydantic error>"`

#### Scenario: Wrong type returns validation error
- **WHEN** execute is called with a parameter value that cannot be coerced to the declared type
- **THEN** execute returns `"Validation error for tool '<name>': <pydantic error>"`

#### Scenario: Valid params dispatched with model_dump
- **WHEN** all required params are present and types are valid
- **THEN** the function is called with `**validated.model_dump()` as keyword arguments
