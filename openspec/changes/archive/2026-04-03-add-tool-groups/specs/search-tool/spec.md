## MODIFIED Requirements

### Requirement: Search matches against name and description
The `search` MCP tool SHALL accept a `query` string and an optional `group` string parameter. When `group` is provided, only tools whose `group` field matches exactly SHALL be candidates for query matching. Query matching (case-insensitive substring against `name` and `description`) SHALL run only against the candidate set. When `group` is not provided, all registered tools are candidates.

#### Scenario: Query matches tool name
- **WHEN** query is `"weather"` and a tool named `get_weather` exists
- **THEN** that tool is included in the results

#### Scenario: Query matches description only
- **WHEN** query does not appear in any tool name but matches a tool's description
- **THEN** those tools are included in the results

#### Scenario: No matches returns informative message
- **WHEN** query matches no tool name or description in the candidate set
- **THEN** search returns `"No tools matched your query."`

#### Scenario: Group filter restricts candidate set
- **WHEN** `group="ops"` is provided and two tools exist — one in group `ops`, one in group `finance`
- **THEN** only the `ops` tool is a candidate, regardless of query

#### Scenario: Group filter with empty query returns all tools in group
- **WHEN** `group="ops"` is provided and `query=""` (empty string)
- **THEN** all tools in group `ops` are returned

#### Scenario: Group filter with no matching tools returns informative message
- **WHEN** `group="nonexistent"` is provided
- **THEN** search returns `"No tools matched your query."`

#### Scenario: No group filter searches all tools
- **WHEN** `group` is not provided
- **THEN** all registered tools are candidates for query matching
