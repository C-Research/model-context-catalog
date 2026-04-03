## ADDED Requirements

### Requirement: Loader class as registry
The system SHALL provide a `Loader` class that subclasses `dict`. A module-level singleton instance `loader` SHALL be exported from `mcc/loader.py`. The registry is the `Loader` instance itself — tool entries are stored as `loader[name]`.

#### Scenario: Registry keyed by tool name
- **WHEN** a tool named `get_weather` is loaded
- **THEN** `loader["get_weather"]` returns the tool entry dict

### Requirement: Loading one or more YAML files
The `Loader` SHALL expose a `load(*paths)` method accepting one or more file paths. Each path is loaded in order via `load_file`. Tools from all files are merged into the same registry. Duplicate names across files SHALL raise a `ValueError`.

#### Scenario: Single file loaded
- **WHEN** `loader.load("tools.yaml")` is called with a valid file
- **THEN** all tools in that file are registered

#### Scenario: Multiple files loaded
- **WHEN** `loader.load("a.yaml", "b.yaml")` is called
- **THEN** tools from both files are merged into the registry

### Requirement: Eager function import at startup
The loader SHALL import all functions at load time using their dotted `fn` path via `importlib`. If any import fails, the loader SHALL raise an error and halt startup.

#### Scenario: Valid fn path imports successfully
- **WHEN** `fn` is a valid dotted path to an importable callable
- **THEN** the function is imported and stored in the registry

#### Scenario: Invalid fn path raises ImportError at startup
- **WHEN** `fn` references a module or attribute that does not exist
- **THEN** loader raises an `ImportError` at startup, not at call time

#### Scenario: fn without dotted path raises ImportError
- **WHEN** `fn` is a bare name with no module prefix
- **THEN** loader raises an `ImportError` with a descriptive message

### Requirement: Per-tool Pydantic model built at load time
For each tool, the loader SHALL construct a Pydantic model using `create_model` based on the parameter definitions. Required parameters (`required: true`) SHALL use `...` as the field default. Optional parameters SHALL use their `default` value (which may be `None`).

#### Scenario: Required parameter enforced
- **WHEN** a parameter is marked `required: true`
- **THEN** the generated Pydantic model raises a `ValidationError` if that parameter is missing

#### Scenario: Optional parameter uses default
- **WHEN** a parameter is `required: false` with `default: "metric"`
- **THEN** the Pydantic model fills in `"metric"` when the parameter is absent
