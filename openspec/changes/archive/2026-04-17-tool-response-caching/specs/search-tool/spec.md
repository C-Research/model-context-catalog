## MODIFIED Requirements

### Requirement: Search registered as FastMCP tool in app.py
The `search` function SHALL be registered on the FastMCP app instance using the `@mcp.tool()` decorator in `mcc/app.py`. It SHALL close over the module-level `loader` singleton from `mcc/loader.py`.

#### Scenario: search is visible as an MCP tool
- **WHEN** the FastMCP app starts
- **THEN** `search` is listed as an available MCP tool

### Requirement: Search matches against name and description
The `search` MCP tool SHALL accept a `query` string and an optional `min_score` float parameter. Matching SHALL be performed via `loader.search(query, min_score)` which delegates to `ToolIndex` using hybrid keyword and semantic search. The local loader dict SHALL NOT be iterated during search.

#### Scenario: Query matches tool name
- **WHEN** query is `"weather"` and a tool named `get_weather` is indexed
- **THEN** that tool is included in the results

#### Scenario: Query matches description only
- **WHEN** query does not appear in any tool name but matches a tool's description
- **THEN** those tools are included in the results

#### Scenario: No matches returns informative message
- **WHEN** query matches no indexed tool
- **THEN** search returns `"No tools matched your query."`

#### Scenario: Fuzzy query matches despite minor typo
- **WHEN** query is `"wether"` (typo) and a tool named `get_weather` is indexed
- **THEN** `get_weather` is included in the results

### Requirement: Search results filtered to caller's accessible tools
The `search` MCP tool SHALL only return tools the caller is authorized to access. The accessible set is determined by `tool.allows(user)`: public tools are always included; authenticated users additionally see tools in their groups and explicitly granted tools.

#### Scenario: Unauthenticated caller sees only public tools
- **WHEN** search is called with no bearer token
- **THEN** only tools with `"public"` in their `groups` appear in results

#### Scenario: Authenticated user sees public tools plus their permitted tools
- **WHEN** search is called by a user in group `ops` with explicit access to `special_tool`
- **THEN** results include public tools, all `ops` group tools, and `special_tool`

#### Scenario: Authenticated user does not see tools outside their access
- **WHEN** search is called by a user in group `ops`
- **THEN** tools in group `finance` (not granted to the user) are not in results

### Requirement: Search results may be served from cache
When `settings.cache.search_ttl > 0`, `loader.search()` SHALL serve results from the cache when available, bypassing the Elasticsearch query.

#### Scenario: Repeated identical search uses cache
- **WHEN** the same query and min_score are searched twice within the TTL window
- **THEN** the second call returns results without querying Elasticsearch
