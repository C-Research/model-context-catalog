## MODIFIED Requirements

### Requirement: Tool catalog defined in YAML
The system SHALL read tool definitions from a YAML file (default `tools.yaml`). The file SHALL be a dict with a required `tools` key (list of tool entries) and an optional `group` key (string). Each entry SHALL define: `name` (string, unique), `fn` (dotted Python import path), and `description` (string). The `parameters` field is optional and defaults to an empty list.

#### Scenario: Valid catalog loads without error
- **WHEN** `tools.yaml` contains a dict with `tools` list and valid tool entries with supported types
- **THEN** all tools are loaded into the registry without error

#### Scenario: File not found raises error
- **WHEN** the path passed to `loader.load()` does not exist
- **THEN** loader raises a `ValueError` at startup

#### Scenario: File root is a list raises error
- **WHEN** `tools.yaml` top-level value is a YAML list (old format)
- **THEN** loader raises a `ValueError` at startup with a message indicating the dict-wrapper format is required

#### Scenario: File root is not a dict raises error
- **WHEN** `tools.yaml` top-level value is neither a list nor a dict
- **THEN** loader raises a `ValueError` at startup

#### Scenario: Missing tools key raises error
- **WHEN** `tools.yaml` root dict is missing the `tools` key
- **THEN** loader raises a `ValueError` at startup

#### Scenario: Duplicate tool name raises error
- **WHEN** two entries share the same `name` (across one or more loaded files)
- **THEN** loader raises a `ValueError` at startup
