## Why

`Loader.save()` unconditionally drops and recreates the shared `ToolIndex` and then reindexes tools one document at a time. This runs on every server boot (`app.py` lifespan) and on every `mcc` CLI invocation except `download` (the CLI group callback), not just on deliberate reindex requests. In production this produces ~100ms windows where the tools index doesn't exist (search calls 404/503 — confirmed against logs, where 503 timestamps line up exactly with delete→create cycles) and a longer window where the index exists but is only partially repopulated (each per-doc write refreshes immediately, so concurrent searches see an incomplete catalog with no error at all). Any routine, read-only command like `mcc user list` currently triggers this against the live index.

## What Changes

- **BREAKING**: Server boot (`mcc/app.py` lifespan) no longer touches the tools index at all — `await loader.save()` is removed from `lifespan` with no replacement.
- **BREAKING**: The `mcc` CLI group callback (`mcc/cli/__init__.py`) no longer calls `loader.save()` before every subcommand. No connectivity-check replacement is added; commands that need Elasticsearch/OpenSearch will surface whatever error the client naturally raises.
- **BREAKING**: `mcc tool reindex` becomes the only operation that ever drops/recreates/populates the tools index. A brand-new or empty Elasticsearch/OpenSearch cluster has no tools index and no tool catalog until `mcc tool reindex` is run explicitly — nothing auto-creates or self-heals it anymore.
- `Loader.save()` reindexes via a single bulk write instead of a per-document loop: it batch-embeds every tool signature in one call, builds the full set of index actions, writes them with one bulk call, then refreshes the index once. This applies identically to both the Elasticsearch and OpenSearch backends.
- Documentation (installation, CLI reference, project docs) is updated to describe the new lifecycle: index population is a deliberate, explicit action, not something that happens automatically at boot or on arbitrary CLI commands.

## Capabilities

### New Capabilities
(none — this changes the behavior of existing capabilities only)

### Modified Capabilities
- `catalog-loader`: `Loader.save()`/`reload()` are no longer invoked automatically at FastMCP lifespan startup or at CLI entrypoint; `save()`'s reindex mechanism changes from a per-document loop to a single batched/bulk write.
- `tool-index`: `ToolIndex` gains a bulk-indexing path (batched embeddings + bulk write + single refresh) implemented symmetrically for both the Elasticsearch and OpenSearch backends, used by `Loader.save()`.

## Impact

- Code: `mcc/app.py` (lifespan), `mcc/cli/__init__.py` (group callback), `mcc/cli/tools.py` (`tool reindex`, unchanged trigger point), `mcc/loader.py` (`Loader.save()`), `mcc/db/base.py` (shared bulk-indexing + batched embedding helpers), `mcc/db/es.py` (Elasticsearch bulk write), `mcc/db/os.py` (OpenSearch bulk write).
- Docs: `docs/getting-started/installation.md`, `docs/cli.md`, `docs/cli/tool.md`, `docs/index.md`, this project's `CLAUDE.md` ("Running the server" section).
- Operational impact: deploy pipelines and fresh-environment setup must explicitly run `mcc tool reindex` after standing up Elasticsearch/OpenSearch and after any tool YAML change intended to reach the live catalog — this no longer happens implicitly.
