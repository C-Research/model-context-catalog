## ADDED Requirements

### Requirement: Search results filtered to caller's accessible tools
The `search` MCP tool SHALL only return tools the caller is authorized to access. The accessible set is determined by `can_access(user, tool_name, tool_entry)` (same logic as execute): public tools are always included; authenticated users additionally see tools in their groups and explicitly granted tools. The `group` filter parameter (if provided) is applied within the accessible set.

#### Scenario: Unauthenticated caller sees only public tools
- **WHEN** search is called with no bearer token
- **THEN** only tools with `group: public` appear in results

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
