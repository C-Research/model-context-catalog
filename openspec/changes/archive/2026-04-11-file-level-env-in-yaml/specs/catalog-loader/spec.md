## MODIFIED Requirements

### Requirement: Loading one or more YAML files
The `Loader` SHALL expose a `load(*paths)` method accepting one or more file paths. Each path is loaded in order via `load_file`. Tools from all files are merged into the same registry. Duplicate keys SHALL raise a `ValueError`. The file-level `groups` value from each file SHALL be used as the default for any tool in that file that does not specify its own `groups`. If a YAML file contains a top-level `env_file` or `env` field, `load_file` SHALL cascade those values into each tool entry as subprocess-environment defaults — tools without their own `env_file` inherit the file-level value; tool-level `env` is merged on top of file-level `env` with tool-level taking precedence. `load()` SHALL remain synchronous and SHALL NOT push to Elasticsearch — callers are responsible for calling `save()` separately.

#### Scenario: Single file loaded
- **WHEN** `loader.load("tools.yaml")` is called with a valid file
- **THEN** all tools in that file are registered with their resolved groups

#### Scenario: Multiple files loaded
- **WHEN** `loader.load("a.yaml", "b.yaml")` is called
- **THEN** tools from both files are merged into the registry

#### Scenario: Tools from different files carry their own groups
- **WHEN** `a.yaml` has `groups: [ops]` and `b.yaml` has `groups: [finance]`
- **THEN** tools from `a.yaml` have `groups = ["ops"]` and tools from `b.yaml` have `groups = ["finance"]`

#### Scenario: load does not push to Elasticsearch
- **WHEN** `loader.load("tools.yaml")` is called without a subsequent `save()`
- **THEN** the tool index in Elasticsearch is not modified

#### Scenario: File-level env_file cascades to tools without their own
- **WHEN** a YAML file has `env_file: secrets.env` and contains a tool with no per-tool `env_file`
- **THEN** that tool's `ToolModel.env_file` is set to `secrets.env` for subprocess use
