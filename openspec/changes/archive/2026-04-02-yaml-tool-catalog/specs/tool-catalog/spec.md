## ADDED Requirements

### Requirement: Tool catalog defined in YAML
The system SHALL read tool definitions from a YAML file (default `tools.yaml`). The file SHALL be a flat list of tool entries at the top level. Each entry SHALL define: `name` (string, unique), `fn` (dotted Python import path), and `description` (string). The `parameters` field is optional and defaults to an empty list.

#### Scenario: Valid catalog loads without error
- **WHEN** `tools.yaml` contains valid tool entries with supported types
- **THEN** all tools are loaded into the registry without error

#### Scenario: File not found raises error
- **WHEN** the path passed to `loader.load()` does not exist
- **THEN** loader raises a `ValueError` at startup

#### Scenario: File is not a list raises error
- **WHEN** `tools.yaml` top-level value is not a YAML list
- **THEN** loader raises a `ValueError` at startup

#### Scenario: Duplicate tool name raises error
- **WHEN** two entries share the same `name` (across one or more loaded files)
- **THEN** loader raises a `ValueError` at startup

### Requirement: Parameter definitions
Each parameter entry SHALL include `name`. The `type` field is optional and defaults to `str` if omitted. The `required` field is optional and defaults to `false` if omitted. The `description` field is optional. An optional `default` field MAY be provided for non-required parameters.

#### Scenario: Omitted type defaults to str
- **WHEN** a parameter entry has no `type` field
- **THEN** the parameter is treated as type `str`

#### Scenario: Omitted required defaults to false
- **WHEN** a parameter entry has no `required` field
- **THEN** the parameter is treated as optional

#### Scenario: Unsupported type raises error
- **WHEN** a parameter specifies a type not in `{str, int, float, bool, list, dict}`
- **THEN** loader raises a `ValueError` at startup

#### Scenario: Optional parameter with default
- **WHEN** a parameter has `required: false` and a `default` value
- **THEN** execute uses the default when that parameter is omitted from the call
