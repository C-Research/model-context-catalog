## MODIFIED Requirements

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
