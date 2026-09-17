## Context

`Loader.save()` (`mcc/loader.py`) drops the `ToolIndex`, recreates it, then indexes tools one at a time via `ToolIndex.index_tool()` → `put()` (`refresh=True` per call). It is invoked from three places:

1. `mcc/app.py` lifespan — every server process boot.
2. `mcc/cli/__init__.py`'s `cli()` group callback — every `mcc` subcommand except `download`.
3. `mcc/cli/tools.py`'s `tool reindex` command — the only call site that represents a deliberate "rebuild the catalog" action.

Production logs show 503s lining up exactly with delete→create cycles (~100ms gap where the index doesn't exist). A second, unlogged window exists too: between `create()` and the end of the per-doc loop, the index exists but is only partially populated, so concurrent searches silently return an incomplete catalog. Call sites 1 and 2 have no legitimate reason to mutate ES tool documents at all — they don't read `ToolIndex`, they exist only so a later `search()` has something to query.

Both backends (`mcc/db/es.py`, `mcc/db/os.py`) already share `ToolIndexMixin`/`IndexLifecycle` in `mcc/db/base.py` for backend-agnostic pieces, with per-client CRUD split into `_ESIndexBase`/`_OSIndexBase`. `elasticsearch.helpers.async_bulk` and `opensearchpy.helpers.async_bulk` have matching signatures (`(client, actions, ...) -> (count, errors)`) and both expect the same `{_index, _id, _source}` action-dict shape, so bulk writes fit that existing split cleanly. `fastembed.TextEmbedding.embed()` already batches internally (`batch_size=256` default) — a batched embedding call is a call with a `list[str]`, not new chunking logic.

## Goals / Non-Goals

**Goals:**
- Eliminate the drop/recreate race entirely for the common path: normal server boots and routine CLI commands never touch the tools index.
- Make `mcc tool reindex` the single, explicit, well-understood trigger for a full tools-index rebuild.
- Reduce the reindex window itself (fewer refreshes, one embedding call) for both backends equally.

**Non-Goals:**
- Not eliminating the drop/recreate gap *during* an explicit `mcc tool reindex` run — that operation still drops and recreates the index; it's just no longer triggered incidentally. (Considered and rejected: alias/blue-green swap, diff-based incremental upsert — both add real complexity for a gap that, once decoupled from boot/CLI-entry, only occurs during a deliberate, operator-initiated action rather than randomly under live traffic.)
- Not adding any distributed lock / leader election for multi-replica coordination — out of scope now that no replica boot touches the index.
- Not touching single-document `put()`/`index_tool()`/`embed()` call sites used elsewhere (audit log, users, keys) — bulk is additive, not a replacement of the single-doc API.
- Not adding a replacement connectivity check to the CLI group callback — commands that need Elasticsearch/OpenSearch will surface the client's native error.

## Decisions

**Boot and CLI-entry no longer call `loader.save()` at all (not even an idempotent `create()`).** `mcc/app.py`'s `lifespan` function is deleted entirely, along with the `lifespan=lifespan` kwarg passed to `FastMCP(...)` — the app relies on FastMCP's own default (no-op) lifespan rather than defining an empty one. `mcc/cli/__init__.py`'s group callback drops its `try: arun(loader.save()) except: err(...)` block entirely (and, since nothing else needed it, the now-unused `@click.pass_context`/`ctx` parameter and the `arun`/`loader` imports). Alternative considered: keep an idempotent `create()`-only call so a fresh cluster self-heals an empty index shape. Rejected — it reintroduces an implicit ES dependency on every boot/command for a benefit (auto-provisioning) that's better served by treating "the tools index exists and is populated" as a deploy-time precondition, satisfied by running `mcc tool reindex` once, the same way a DB migration is a deploy step rather than something every replica does independently.

**`mcc tool reindex` remains a full drop+recreate+repopulate, not an incremental diff.** Alternative considered: diff-based upsert (compute added/changed/removed keys, `put`/`delete` only the delta, never `drop()`). Rejected for this change — it's a larger behavior change to get right (needs correct handling of mapping changes, orphaned docs, etc.) for a operation that, once decoupled from boot and every CLI command, runs rarely and deliberately. Revisit only if `mcc tool reindex` itself becomes a frequent enough operation that its own drop/recreate window matters.

**`mcc/db/*` gains only a bulk write primitive; the batching/orchestration logic lives in `Loader.save()`.** `mcc/db/base.py` gains `embed_batch(texts: list[str]) -> list[list[float]]` (same `run_in_executor` pattern as the existing single-text `embed()`, but calls `_get_model().embed(texts)` once), and each backend gains `bulk_put(actions: list[dict]) -> None` as a CRUD primitive alongside `put`/`get`/`search`/`create`/`drop`: `_ESIndexBase.bulk_put` wraps `elasticsearch.helpers.async_bulk`, `_OSIndexBase.bulk_put` wraps `opensearchpy.helpers.async_bulk`; both refresh once after the bulk write. Alternative considered (and initially implemented, then reverted): a shared `ToolIndexMixin.bulk_index_tools(tools: list[ToolModel])` that did the batch-embed + action-building + `bulk_put` call itself. Rejected — `mcc/db/*` is scoped to backend CRUD primitives, not tool-catalog-specific orchestration; declaring `ToolIndexMixin`'s `self._client`'s type for the refresh call also narrowed it across the whole `ToolIndex` class via multiple inheritance and broke `search()`/`signatures()`'s use of the same attribute. Keeping `bulk_put` as a plain `{_index, _id, _source}` action-list primitive avoids that entirely.

**`Loader.save()` builds the bulk actions and calls `ToolIndex.bulk_put()` directly.** It batch-embeds `[tool.signature for tool in self.values()]` via `embed_batch`, zips the resulting vectors with the tools to build one `{_index: settings.TOOL_INDEX, _id: tool.key, _source: {...}}` action per tool, then calls `await idx.bulk_put(actions)` inside the same `drop()`/`create()` bracket as today — replacing the old `for tool in self.values(): await idx.index_tool(tool)` loop.

## Risks / Trade-offs

- **[Fresh/empty cluster has no tools index until `mcc tool reindex` runs]** → Mitigation: document it explicitly as a required first-run/deploy step (installation docs, CLI docs, this project's `CLAUDE.md`). No auto-provisioning fallback is added, by design.
- **[Removing the CLI group callback's try/except also removes today's friendly "ES Connection error" message for unrelated commands]** → Accepted trade-off: commands that don't touch ES (most of them) no longer need ES reachable at all, which is a net improvement; commands that do touch ES will surface the underlying client exception directly.
- **[`mcc tool reindex` still has a real drop→create gap during the (now rare, deliberate) rebuild]** → Mitigation: none added in this change; documented as a known, accepted limitation of staying within the C+D scope (see Non-Goals). Operators should avoid running it against a cluster serving heavy concurrent search traffic if that gap matters to them.
- **[Batch-embedding the full tool set in one call increases peak memory during reindex]** → fastembed's own `batch_size=256` internal chunking bounds this; not expected to matter at mcc's tool-catalog scale, but worth a note if a catalog ever grows into the tens of thousands of tools.

## Migration Plan

- Ship the code changes and updated docs together (no backwards-compatibility shim, no feature flag).
- Deploy pipelines must run `mcc tool reindex` once against the target Elasticsearch/OpenSearch cluster before or immediately after rolling out a version that includes this change, and after any subsequent tool-YAML change meant to reach the live catalog.
- No data migration needed — the tools index's mapping and document shape are unchanged; only the write path and its trigger points change.
