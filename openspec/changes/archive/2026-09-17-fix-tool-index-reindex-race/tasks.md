## 1. Bulk write primitive (`mcc/db/base.py`) — CRUD only, no tool-catalog orchestration

- [x] 1.1 Add `embed_batch(texts: list[str]) -> list[list[float]]`, mirroring `embed()`'s `run_in_executor` pattern but calling `_get_model().embed(texts)` once for the whole list.
- [x] 1.2 Declare `bulk_put(actions: list[dict]) -> None` as part of the `TYPE_CHECKING`-guarded protocol on `ToolIndexMixin`, alongside the existing `put` stub. (Revised from the original plan: no `ToolIndexMixin.bulk_index_tools()` — that orchestration moved to `Loader.save()` per task 3.1, so `mcc/db/*` stays limited to CRUD primitives.)

## 2. Backend-specific bulk writes

- [x] 2.1 `mcc/db/es.py`: add `_ESIndexBase.bulk_put(actions)` using `from elasticsearch.helpers import async_bulk`, calling `await async_bulk(self._client, actions)`, then refreshing once.
- [x] 2.2 `mcc/db/os.py`: add `_OSIndexBase.bulk_put(actions)` using `from opensearchpy.helpers import async_bulk`, calling `await async_bulk(self._client, actions)`, then refreshing once.

## 3. Loader changes (`mcc/loader.py`)

- [x] 3.1 In `Loader.save()`, replace the `for tool in self.values(): await idx.index_tool(tool)` loop with: batch-embed `[tool.signature for tool in tools]` via `embed_batch`, build one `{_index: settings.TOOL_INDEX, _id: tool.key, _source: {signature, groups, embedding}}` action per tool, then `await idx.bulk_put(actions)` — inside the same `drop()`/`create()` bracket as today. The batching/action-building logic lives in `Loader.save()`, not in `mcc/db/*`.

## 4. Remove incidental index writes from boot and CLI entry

- [x] 4.1 `mcc/app.py`: delete the `lifespan` function entirely (not just empty its body) and drop the `lifespan=lifespan` kwarg from the `FastMCP(...)` call — the app relies on FastMCP's own default lifespan.
- [x] 4.2 `mcc/cli/__init__.py`: delete the `if ctx.invoked_subcommand != "download": try: arun(loader.save()) except Exception as exc: err(...)` block from the `cli()` group callback entirely (no replacement). Also dropped the now-unused `@click.pass_context`/`ctx` param and the `arun`/`loader` imports, since nothing else in the file used them.
- [x] 4.3 Confirmed `mcc/cli/tools.py`'s `tool reindex` command (`loader.reload()` → `save()`) is unchanged and remains the only trigger for a full tools-index rebuild. Verified `mcc --help` and `mcc tool list` run cleanly with no ES touch.

## 5. Tests

- [x] 5.1 Added `TestLoaderSaveBulk` in `tests/test_tool_index.py` covering `Loader.save()`'s bulk path against the real Elasticsearch test index: one `embed_batch` call with all signatures, one `ToolIndex.bulk_put` call with all actions, and a no-op-safe empty-catalog case. Existing `TestLoaderSave`/`TestLoaderSearch*` tests already cover correct stored/queryable documents end-to-end.
- [x] 5.2 Added `tests/test_tool_index_opensearch.py`: unit tests for `_OSIndexBase.bulk_put` against a fake client (no live OpenSearch cluster in this environment/repo's test setup), skipped via `pytest.importorskip("opensearchpy")` when the optional extra isn't installed. Verifies one `async_bulk` call and exactly one `indices.refresh` call.
- [x] 5.3 No test added: `lifespan` was deleted entirely (task 4.1), so there is no code path left that could call `loader.save()` at startup — confirmed by `grep -rn "lifespan" mcc/ tests/ docs/` returning no results.
- [x] 5.4 Added `TestNonReindexCommandsDoNotTouchToolIndex` in `tests/test_tools_cli.py`: invokes `mcc tool list` against a freshly-created empty `tool_idx` and asserts the index is still empty afterward, contrasting with `TestToolReindex` (which asserts `tool reindex` *does* populate it).
- [x] 5.5 Ran the full check suite: `uv run pytest` (548 passed), `uv run pyright` (0 errors in any changed file; 7 pre-existing errors remain in unrelated, untouched `toolsets/` files with missing optional third-party deps), `uv run ruff check .` (all checks passed), `uv run bandit -c pyproject.toml -r .` (one low-severity finding, in an unrelated pre-existing untracked `scripts/check_search_index.py`, not touched by this change).

## 6. Documentation

- [x] 6.1 `docs/getting-started/installation.md`: added a "Populate the tool catalog" section noting the index is never auto-created/populated and `mcc tool reindex` must be run once (and after tool YAML changes).
- [x] 6.2 `docs/cli.md` and `docs/cli/tool.md` (`reindex` section): noted `tool reindex` is now the only operation that ever touches the tools index, and that it fully rebuilds (drop+recreate+bulk) rather than incrementally updating.
- [x] 6.3 `docs/index.md`: removed the "Hot reload" bullet entirely rather than reword it — on inspection it overstated what's actually possible (`mcc tool reindex` only updates the search index; it can't reach an already-running server's in-memory tool dict), and there's no shipped mechanism that does what the bullet claimed.
- [x] 6.4 This project's `CLAUDE.md` "Running the server" section: added the same first-run note about requiring `mcc tool reindex`.
