## ADDED Requirements

### Requirement: Search registered as FastMCP tool in app.py
The `search` function SHALL be registered on the FastMCP app instance using the `@mcp.tool()` decorator in `mcc/app.py`. It SHALL close over the module-level `loader` singleton from `mcc/loader.py`.

#### Scenario: search is visible as an MCP tool
- **WHEN** the FastMCP app starts
- **THEN** `search` is listed as an available MCP tool

### Requirement: Search matches against name and description
The `search` MCP tool SHALL accept a `query` string and an optional `group` string parameter. Matching SHALL be performed via `loader.search(query, group)` which delegates to `ToolIndex` using a `multi_match` ES query across `name` (boosted 2×) and `description` with `fuzziness: AUTO`. When `group` is provided, only tools whose `groups` field contains that value SHALL be candidates. The local loader dict SHALL NOT be iterated during search.

#### Scenario: Query matches tool name
- **WHEN** query is `"weather"` and a tool named `get_weather` is indexed
- **THEN** that tool is included in the results

#### Scenario: Query matches description only
- **WHEN** query does not appear in any tool name but matches a tool's description
- **THEN** those tools are included in the results

#### Scenario: No matches returns informative message
- **WHEN** query matches no indexed tool
- **THEN** search returns `"No tools matched your query."`

#### Scenario: Group filter restricts candidate set
- **WHEN** `group="ops"` is provided and two tools exist — one with `groups=["ops"]`, one with `groups=["finance"]`
- **THEN** only the `ops` tool is a candidate, regardless of query

#### Scenario: Group filter with no matching tools returns informative message
- **WHEN** `group="nonexistent"` is provided
- **THEN** search returns `"No tools matched your query."`

#### Scenario: No group filter searches all tools
- **WHEN** `group` is not provided
- **THEN** all indexed tools are candidates for query matching

#### Scenario: Fuzzy query matches despite minor typo
- **WHEN** query is `"wether"` (typo) and a tool named `get_weather` is indexed
- **THEN** `get_weather` is included in the results

### Requirement: Search results include call signature
Each result SHALL be formatted as two lines: `<name> — <description>` followed by an indented `execute("<name>", {<sig>})` call. The signature SHALL list each parameter as `name: type` (required) or `name?: type = default` (optional), joined by `, `.

#### Scenario: Result format for a tool with mixed params
- **WHEN** a tool has one required param `city: str` and one optional param `units: str = "metric"`
- **THEN** the result shows `execute("get_weather", {city: str, units?: str = metric})`

#### Scenario: Multiple results separated by blank line
- **WHEN** multiple tools match the query
- **THEN** results are joined with `"\n\n"`

### Requirement: Search results filtered to caller's accessible tools
The `search` MCP tool SHALL only return tools the caller is authorized to access. The accessible set is determined by `can_access(user, tool_name, tool_entry)` (same logic as execute): public tools are always included; authenticated users additionally see tools in their groups and explicitly granted tools. The `group` filter parameter (if provided) is applied within the accessible set.

#### Scenario: Unauthenticated caller sees only public tools
- **WHEN** search is called with no bearer token
- **THEN** only tools with `"public"` in their `groups` appear in results

#### Scenario: Authenticated user sees public tools plus their permitted tools
- **WHEN** search is called by a user in group `ops` with explicit access to `special_tool`
- **THEN** results include public tools, all `ops` group tools, and `special_tool`

#### Scenario: Authenticated user does not see tools outside their access
- **WHEN** search is called by a user in group `ops`
- **THEN** tools in group `finance` (not granted to the user) are not in results

#### Scenario: Group filter applies within accessible set
- **WHEN** search is called with `group="ops"` by a user in group `ops`
- **THEN** only `ops` tools the user can access are returned

#### Scenario: Group filter for inaccessible group returns no results
- **WHEN** search is called with `group="finance"` by a user not in `finance`
- **THEN** search returns `"No tools matched your query."`
