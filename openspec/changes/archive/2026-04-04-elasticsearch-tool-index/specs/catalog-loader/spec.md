## ADDED Requirements

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

## MODIFIED Requirements

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
