## ADDED Requirements

### Requirement: Tools belong to one or more groups
A tool SHALL have a `groups` field of type `list[str]`. A tool MAY belong to multiple groups simultaneously. There is no limit on the number of groups a tool can belong to.

#### Scenario: Tool with a single group
- **WHEN** a tool is loaded from a file with `groups: [ops]`
- **THEN** `tool.groups == ["ops"]`

#### Scenario: Tool with multiple groups
- **WHEN** a tool entry specifies `groups: [admin, data]`
- **THEN** `tool.groups == ["admin", "data"]` (or any order — membership is a set)

### Requirement: Default groups when none specified
When a tool is loaded and no `groups` is defined (neither at the file level nor on the tool entry), the loader SHALL assign `groups = ["public"]` as the default.

#### Scenario: File with no groups key defaults all tools to public
- **WHEN** a YAML file has no `groups` key and defines a tool
- **THEN** that tool is registered with `groups = ["public"]`

#### Scenario: Tool entry with no groups inherits file-level groups
- **WHEN** a YAML file has `groups: [ops]` and a tool entry has no `groups` key
- **THEN** that tool is registered with `groups = ["ops"]`

#### Scenario: Tool entry groups override file-level groups
- **WHEN** a YAML file has `groups: [ops]` and a tool entry specifies `groups: [admin, data]`
- **THEN** that tool is registered with `groups = ["admin", "data"]`

### Requirement: Tool key derived from sorted groups and name
The tool's registry key SHALL be computed as `".".join(sorted(groups) + [name])`. This ensures the key is deterministic regardless of the order groups are declared, and that two tools with the same name but different group sets get distinct keys.

#### Scenario: Single-group key
- **WHEN** a tool named `list_users` has `groups = ["admin"]`
- **THEN** its key is `"admin.list_users"`

#### Scenario: Multi-group key is sorted
- **WHEN** a tool named `my_tool` has `groups = ["data", "admin"]`
- **THEN** its key is `"admin.data.my_tool"` (groups sorted alphabetically)

#### Scenario: Same key regardless of groups declaration order
- **WHEN** one tool declares `groups: [data, admin]` and another declares `groups: [admin, data]` with the same name
- **THEN** both produce the same key and the second registration raises a `ValueError`

#### Scenario: Ungrouped tool key is just the name
- **WHEN** a tool named `echo` has `groups = []`
- **THEN** its key is `"echo"`

### Requirement: Group membership used for access control
The `can_access` function SHALL check whether `"public"` is in `tool.groups` (unrestricted access) or whether any element of `tool.groups` appears in the user's `groups` list (group-based access).

#### Scenario: Tool accessible when user shares any group
- **WHEN** a tool has `groups = ["ops", "data"]` and a user has `groups = ["data"]`
- **THEN** `can_access` returns `True`

#### Scenario: Tool inaccessible when user shares no groups
- **WHEN** a tool has `groups = ["ops", "data"]` and a user has `groups = ["finance"]`
- **THEN** `can_access` returns `False` (unless admin or explicit tool grant)
