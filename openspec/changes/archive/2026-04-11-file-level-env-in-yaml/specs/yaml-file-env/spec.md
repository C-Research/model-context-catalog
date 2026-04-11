## ADDED Requirements

### Requirement: File-level env_file field
A tool YAML file SHALL support a top-level `env_file` field. Its value is a path to a dotenv-format file. The loader SHALL cascade this value to every tool entry in the file that does not already have its own `env_file`, setting it as the tool's subprocess environment source. Tools with an explicit per-tool `env_file` are unaffected.

#### Scenario: Tool without env_file inherits file-level env_file
- **WHEN** a YAML file has `env_file: secrets.env` at the top level and a tool entry with no `env_file`
- **THEN** that tool's `ToolModel.env_file` is set to `secrets.env`

#### Scenario: Per-tool env_file is not overridden
- **WHEN** a YAML file has `env_file: catalog.env` and a tool entry with `env_file: tool.env`
- **THEN** that tool's `ToolModel.env_file` remains `tool.env`

### Requirement: File-level env block
A tool YAML file SHALL support a top-level `env` field containing a mapping of key-value pairs. The loader SHALL merge this mapping into every tool entry's `env`, with per-tool values taking precedence over file-level values on key conflicts.

#### Scenario: Tool inherits file-level env
- **WHEN** a YAML file has `env: {KEY_A: val_a}` and a tool entry with no `env`
- **THEN** that tool's `ToolModel.env` is `{KEY_A: val_a}`

#### Scenario: Per-tool env wins on conflict
- **WHEN** a YAML file has `env: {KEY_A: file_val}` and a tool entry with `env: {KEY_A: tool_val, KEY_B: b}`
- **THEN** that tool's `ToolModel.env` is `{KEY_A: tool_val, KEY_B: b}`

#### Scenario: File-level env keys not in per-tool env are inherited
- **WHEN** a YAML file has `env: {KEY_A: a, KEY_B: b}` and a tool entry with `env: {KEY_A: override}`
- **THEN** that tool's `ToolModel.env` contains `KEY_B: b` inherited from the file level
