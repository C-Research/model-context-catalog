## ADDED Requirements

### Requirement: File-level group key in YAML
A YAML tool file MAY include a top-level `group` key (string). When present, its value SHALL be assigned as the group for every tool defined in that file's `tools` list. When absent or null, tools in that file are ungrouped (`group: None`).

#### Scenario: File with group key assigns group to all tools
- **WHEN** a YAML file has `group: ops` and defines two tools
- **THEN** both tools are registered with `group = "ops"`

#### Scenario: File without group key leaves tools ungrouped
- **WHEN** a YAML file has no `group` key and defines a tool
- **THEN** that tool is registered with `group = None`

#### Scenario: File with null group leaves tools ungrouped
- **WHEN** a YAML file has `group: null` and defines a tool
- **THEN** that tool is registered with `group = None`

### Requirement: Group stored in registry entry
Each registry entry SHALL include a `group` field of type `str | None`. This field is set at load time from the file-level group and is immutable after registration.

#### Scenario: Registry entry contains group field
- **WHEN** a tool from a file with `group: finance` is loaded
- **THEN** `loader["tool_name"]["group"]` returns `"finance"`

#### Scenario: Registry entry group is None for ungrouped tool
- **WHEN** a tool from a file with no group key is loaded
- **THEN** `loader["tool_name"]["group"]` returns `None`

### Requirement: One group per tool
A tool SHALL belong to at most one group. There is no mechanism to assign multiple groups to a single tool.

#### Scenario: Tool has exactly one group
- **WHEN** a tool is loaded from a file with `group: ops`
- **THEN** the tool has exactly one group value: `"ops"`
