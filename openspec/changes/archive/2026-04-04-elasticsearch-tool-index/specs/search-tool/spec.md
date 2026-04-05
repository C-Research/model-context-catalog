## MODIFIED Requirements

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
