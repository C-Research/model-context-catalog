## ADDED Requirements

### Requirement: Search registered as FastMCP tool in app.py
The `search` function SHALL be registered on the FastMCP app instance using the `@mcp.tool()` decorator in `mcc/app.py`. It SHALL close over the module-level `loader` singleton from `mcc/loader.py`.

#### Scenario: search is visible as an MCP tool
- **WHEN** the FastMCP app starts
- **THEN** `search` is listed as an available MCP tool

### Requirement: Search matches against name and description
The `search` MCP tool SHALL accept a `query` string and return all registry entries where the query appears (case-insensitive substring) in the tool's `name` or `description`.

#### Scenario: Query matches tool name
- **WHEN** query is `"weather"` and a tool named `get_weather` exists
- **THEN** that tool is included in the results

#### Scenario: Query matches description only
- **WHEN** query does not appear in any tool name but matches a tool's description
- **THEN** those tools are included in the results

#### Scenario: No matches returns informative message
- **WHEN** query matches no tool name or description
- **THEN** search returns `"No tools matched your query."`

### Requirement: Search results include call signature
Each result SHALL be formatted as two lines: `<name> — <description>` followed by an indented `execute("<name>", {<sig>})` call. The signature SHALL list each parameter as `name: type` (required) or `name?: type = default` (optional), joined by `, `.

#### Scenario: Result format for a tool with mixed params
- **WHEN** a tool has one required param `city: str` and one optional param `units: str = "metric"`
- **THEN** the result shows `execute("get_weather", {city: str, units?: str = metric})`

#### Scenario: Multiple results separated by blank line
- **WHEN** multiple tools match the query
- **THEN** results are joined with `"\n\n"`
