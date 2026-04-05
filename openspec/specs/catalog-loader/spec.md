## ADDED Requirements

### Requirement: Loader class as registry
The system SHALL provide a `Loader` class that subclasses `dict`. A module-level singleton instance `loader` SHALL be exported from `mcc/loader.py`. The registry is the `Loader` instance itself — tool entries are stored as `loader[key]` where key is `".".join(sorted(groups) + [name])`.

#### Scenario: Registry keyed by sorted groups and name
- **WHEN** a tool named `get_weather` with `groups = ["ops"]` is loaded
- **THEN** `loader["ops.get_weather"]` returns the tool entry

#### Scenario: Multi-group key is deterministic
- **WHEN** a tool named `my_tool` with `groups = ["data", "admin"]` is loaded
- **THEN** `loader["admin.data.my_tool"]` returns the tool entry

### Requirement: Loading one or more YAML files
The `Loader` SHALL expose a `load(*paths)` method accepting one or more file paths. Each path is loaded in order via `load_file`. Tools from all files are merged into the same registry. Duplicate keys SHALL raise a `ValueError`. The file-level `groups` value from each file SHALL be used as the default for any tool in that file that does not specify its own `groups`. `load()` SHALL remain synchronous and SHALL NOT push to Elasticsearch — callers are responsible for calling `save()` separately.

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

### Requirement: Default groups at load time
When `load_file` reads a YAML file with no top-level `groups` key, it SHALL use `["public"]` as the default groups for all tools in that file. A per-tool `groups` key always takes precedence over the file-level default.

#### Scenario: File with no groups defaults tools to public
- **WHEN** a YAML file has no `groups` key
- **THEN** all tools in that file have `groups = ["public"]`

#### Scenario: Per-tool groups override file-level groups
- **WHEN** a YAML file has `groups: [ops]` and one tool entry has `groups: [admin]`
- **THEN** that tool has `groups = ["admin"]`, others have `groups = ["ops"]`

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

### Requirement: Loader.save() pushes entire store to ToolIndex
The `Loader` class SHALL expose an `async def save(self) -> None` method. When called, it SHALL drop the tool index, recreate it, and put every tool currently in the local dict into `ToolIndex`. This ensures ES exactly mirrors the in-memory store, with no stale entries from previously loaded tools.

#### Scenario: sync overwrites the entire tool index
- **WHEN** the loader has three tools registered and `save()` is called
- **THEN** the tool index contains exactly those three tools

#### Scenario: sync removes stale tools from previous load
- **WHEN** a tool existed in ES from a prior sync but is no longer in the loader dict
- **THEN** after `save()`, that tool is absent from the tool index

#### Scenario: sync is called at FastMCP lifespan startup
- **WHEN** the FastMCP app starts
- **THEN** `loader.save()` is awaited before the app begins serving requests

#### Scenario: sync is called at CLI entrypoint
- **WHEN** any `mcc` CLI command is invoked
- **THEN** `loader.save()` is called before the subcommand executes

### Requirement: Loader.reload() is async and calls save()
The `Loader.reload()` method SHALL be `async def`. After clearing and reloading all registered paths into the local dict, it SHALL call `await self.save()` to propagate changes to ES.

#### Scenario: reload rebuilds dict then syncs to ES
- **WHEN** `await loader.reload()` is called
- **THEN** the local dict is repopulated from YAML files and the tool index is updated to match

### Requirement: Loader.search() resolves ES keys against local dict
The `Loader` class SHALL expose an `async def search(self, query: str, group: str | None = None) -> list[ToolModel]` method. It SHALL call `ToolIndex.search()` to obtain a list of matching tool keys, then resolve each key against the local dict (`self[key]`) to return full `ToolModel` instances. Keys not present in the local dict SHALL be silently skipped. The loader dict SHALL NOT be iterated during search.

#### Scenario: search returns full ToolModels without re-introspection
- **WHEN** `await loader.search("weather")` is called
- **THEN** ES returns matching keys, and each key is resolved from the loader dict — no callable re-resolution occurs

#### Scenario: keys missing from loader are skipped
- **WHEN** ES returns a key that is no longer in the loader dict
- **THEN** that key is omitted from the result silently
