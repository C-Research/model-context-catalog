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

### Requirement: RBAC enforcement before dispatch
The `execute` MCP tool SHALL check whether the caller is authorized to execute the requested tool before dispatching. Authorization SHALL be determined by `can_access(user, tool)`: returns `True` if `"public"` is in `tool.groups`, or if the user is in `admin` group, or if any of `tool.groups` appears in `user["groups"]`, or if `tool.key` is in `user["tools"]`. If the caller is not authorized, `execute` SHALL return `"Unauthorized"` without dispatching the function.

#### Scenario: Public tool accessible without auth
- **WHEN** execute is called for a tool with `"public"` in its `groups` and no bearer token was provided
- **THEN** the tool is dispatched normally

#### Scenario: Authorized user can execute tool in their group
- **WHEN** execute is called by a user whose groups include the tool's group
- **THEN** the tool is dispatched normally

#### Scenario: Authorized user can execute explicitly granted tool
- **WHEN** execute is called by a user who has the tool name in their explicit tools list
- **THEN** the tool is dispatched normally

#### Scenario: Unauthenticated caller blocked from non-public tool
- **WHEN** execute is called with no bearer token for a tool not in the `public` group
- **THEN** execute returns `"Unauthorized"`

#### Scenario: Authenticated user blocked from tool outside their access
- **WHEN** execute is called by a user whose groups and explicit tools do not include the requested tool
- **THEN** execute returns `"Unauthorized"`
