## MODIFIED Requirements

### Requirement: Loading one or more YAML files
The `Loader` SHALL expose a `load(*paths)` method accepting one or more file paths. Each path is loaded in order via `load_file`. Tools from all files are merged into the same registry. Duplicate names across files SHALL raise a `ValueError`. The file-level `group` value from each file SHALL be propagated to all tools registered from that file.

#### Scenario: Single file loaded
- **WHEN** `loader.load("tools.yaml")` is called with a valid file
- **THEN** all tools in that file are registered with their file-level group

#### Scenario: Multiple files loaded
- **WHEN** `loader.load("a.yaml", "b.yaml")` is called
- **THEN** tools from both files are merged into the registry, each carrying the group from their respective file

#### Scenario: Tools from different files carry their own group
- **WHEN** `a.yaml` has `group: ops` and `b.yaml` has `group: finance`
- **THEN** tools from `a.yaml` have `group = "ops"` and tools from `b.yaml` have `group = "finance"`

## ADDED Requirements

### Requirement: load_file returns group alongside tools
The `load_file` function SHALL return both the list of `ToolModel` instances and the file-level group value (`str | None`). The group is read from the root dict's `group` key and defaults to `None` if absent or null.

#### Scenario: load_file extracts group from root dict
- **WHEN** the YAML root dict contains `group: ops`
- **THEN** `load_file` returns `group = "ops"` alongside the tool list

#### Scenario: load_file returns None group when key absent
- **WHEN** the YAML root dict has no `group` key
- **THEN** `load_file` returns `group = None`

### Requirement: Loader.register accepts group parameter
The `Loader.register` method SHALL accept an optional `group: str | None` parameter and store it in the registry entry under the `"group"` key.

#### Scenario: Registered tool carries group in entry
- **WHEN** `loader.register(tool, group="ops")` is called
- **THEN** `loader[tool.name]["group"]` equals `"ops"`

#### Scenario: Registered tool with no group stores None
- **WHEN** `loader.register(tool)` is called without a group argument
- **THEN** `loader[tool.name]["group"]` is `None`
