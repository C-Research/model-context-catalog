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
The `Loader` class SHALL expose an `async def save(self) -> None` method. When called, it SHALL drop the tool index, recreate it, batch-embed every tool signature in the local dict in a single embedding call, build the corresponding `{_index, _id, _source}` actions itself, and write them via `ToolIndex.bulk_put()` (one bulk write, one refresh). This ensures ES/OpenSearch exactly mirrors the in-memory store, with no stale entries from previously loaded tools, and without indexing tools one document at a time. The batching/action-building logic lives in `Loader.save()` itself, not in the `ToolIndex`/`ToolIndexMixin` classes — `mcc/db/*` stays limited to CRUD primitives (`put`, `bulk_put`, `get`, `search`, `create`, `drop`); tool-catalog-specific orchestration belongs to the loader that owns the catalog.

`save()` SHALL NOT be invoked automatically at FastMCP lifespan startup, nor automatically before any `mcc` CLI subcommand. It SHALL only run when explicitly triggered — currently, only via `mcc tool reindex` (which calls `Loader.reload()` → `save()`). Server boot and other CLI commands SHALL NOT touch the tool index in any way (no drop, no create, no read). There SHALL be no FastMCP lifespan hook at all in `mcc/app.py` for this purpose — the app SHALL rely on FastMCP's own default (no-op) lifespan rather than defining an empty one.

#### Scenario: sync overwrites the entire tool index
- **WHEN** the loader has three tools registered and `save()` is called
- **THEN** the tool index contains exactly those three tools

#### Scenario: sync removes stale tools from previous load
- **WHEN** a tool existed in ES from a prior sync but is no longer in the loader dict
- **THEN** after `save()`, that tool is absent from the tool index

#### Scenario: sync uses one bulk write with batched embeddings
- **WHEN** `save()` is called with N tools registered
- **THEN** all N tool signatures are embedded in a single batched embedding call, all N documents are written via a single bulk write, and the index is refreshed exactly once — not N times

#### Scenario: FastMCP lifespan startup does not sync
- **WHEN** the FastMCP app starts
- **THEN** `loader.save()` is NOT called, and the tool index is left exactly as it was before the process started

#### Scenario: CLI entrypoint does not sync
- **WHEN** any `mcc` CLI command is invoked (including commands other than `tool reindex`)
- **THEN** `loader.save()` is NOT called as part of invoking the CLI, and the tool index is left exactly as it was before the command ran

#### Scenario: A fresh cluster has no tool index until reindex is run
- **WHEN** the configured Elasticsearch/OpenSearch cluster has never had `mcc tool reindex` run against it
- **THEN** the tool index does not exist, and `search()` against it returns no results (or a not-found error) until `mcc tool reindex` is run explicitly

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
