## ADDED Requirements

### Requirement: ToolIndex class backed by Elasticsearch
The system SHALL provide a `ToolIndex` class in `mcc/db.py` that subclasses `ESIndex`. Its index name SHALL be read from `settings.ELASTICSEARCH.TOOL_INDEX`. It SHALL define an ES mapping with only the fields needed for search: `name` as `text`, `description` as `text`, and `groups` as `keyword`. The document ID SHALL be `tool.key`.

#### Scenario: ToolIndex uses configured tool index name
- **WHEN** `settings.ELASTICSEARCH.TOOL_INDEX` is `"mcc-tools"`
- **THEN** all ToolIndex operations target the `mcc-tools` ES index

### Requirement: ToolIndex stores only search fields
`ToolIndex` SHALL expose `put(tool: ToolModel) -> None` and `delete(id: str) -> None`. `put` SHALL store only `{name, description, groups}` — no `fn`, `params`, or `callable`. The document ID SHALL be `tool.key`.

#### Scenario: put stores only search-relevant fields
- **WHEN** a `ToolModel` is put into the index
- **THEN** the stored ES document contains only `name`, `description`, and `groups`

#### Scenario: delete removes a tool from the index
- **WHEN** `delete(key)` is called for an indexed tool
- **THEN** that document is removed from the index

### Requirement: ToolIndex search returns keys
`ToolIndex` SHALL expose `search(query: str, group: str | None = None) -> list[str]` returning document IDs (tool keys). The query SHALL be matched against `name` (boosted 2×) and `description` using a `multi_match` query with `fuzziness: AUTO`. When `group` is provided, results SHALL be filtered to tools whose `groups` field contains that value.

#### Scenario: Search returns matching tool keys
- **WHEN** query is `"weather"` and a tool with key `"ops.get_weather"` is indexed
- **THEN** `"ops.get_weather"` is included in the returned key list

#### Scenario: Search matches on description
- **WHEN** query text appears only in a tool's description, not its name
- **THEN** that tool's key is included in results

#### Scenario: Fuzzy search tolerates minor typos
- **WHEN** query is `"wether"` (typo) and a tool named `get_weather` is indexed
- **THEN** that tool's key is included in results

#### Scenario: Group filter restricts results
- **WHEN** `group="ops"` is provided and two tools exist with groups `["ops"]` and `["finance"]`
- **THEN** only the `ops` tool's key is returned

#### Scenario: Empty results return empty list
- **WHEN** the query matches no indexed tools
- **THEN** `search()` returns an empty list

### Requirement: Settings split for user and tool indices
The `elasticsearch` settings block SHALL use `user_index` for the user store index name and `tool_index` for the tool store index name, replacing the previous single `index` key. Default values SHALL be `mcc-users` and `mcc-tools` respectively.

#### Scenario: UsersIndex reads user_index setting
- **WHEN** `settings.ELASTICSEARCH.USER_INDEX` is `"mcc-users"`
- **THEN** `UsersIndex` targets the `mcc-users` ES index

#### Scenario: ToolIndex reads tool_index setting
- **WHEN** `settings.ELASTICSEARCH.TOOL_INDEX` is `"mcc-tools"`
- **THEN** `ToolIndex` targets the `mcc-tools` ES index
