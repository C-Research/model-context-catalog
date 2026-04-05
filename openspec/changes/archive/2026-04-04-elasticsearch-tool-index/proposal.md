## Why

The tool catalog currently lives only in memory (a dict built from YAML files at startup), making search limited to simple substring matching. Moving tools into Elasticsearch as a search-optimized datastore enables full-text, fuzzy, and field-boosted search without changing the YAML files as the source of truth.

## What Changes

- **New `ToolIndex`** — an `ESIndex` subclass for the tool catalog with CRUD methods returning `ToolModel`
- **Split ES index settings** — `elasticsearch.index` replaced with `elasticsearch.user_index` and `elasticsearch.tool_index` **BREAKING**
- **`Loader.save()`** — new async method that drops, recreates, and repopulates the tool index from the in-memory dict
- **`Loader.reload()`** — becomes async; calls `save()` after rebuilding the dict
- **`Loader.search()`** — new async method delegating to `ToolIndex` ES search (replaces inline dict iteration)
- **`search` MCP tool** — updated to call `loader.search()` instead of iterating the dict
- **App lifespan** — FastMCP startup calls `loader.save()` to populate ES on boot
- **CLI main group** — calls `loader.save()` before any subcommand runs
- **Test fixtures** — `conftest.py` updated for split index env vars; tool search tests get a `_fresh_tool_index` fixture

## Capabilities

### New Capabilities

- `tool-index`: Elasticsearch-backed index for tool storage and full-text search

### Modified Capabilities

- `catalog-loader`: Loader gains `save()` and async `reload()`; `search()` delegates to ES
- `search-tool`: Search now uses ES multi-match with fuzziness instead of substring matching

## Impact

- `mcc/db.py` — no changes to `ESIndex` base
- `mcc/auth/db.py` — `UsersIndex.index` reads `USER_INDEX` instead of `INDEX`
- `mcc/loader.py` — `save()`, `search()` added; `reload()` becomes async
- `mcc/app.py` — lifespan added; `search` tool updated
- `mcc/cli.py` — `cli` group calls `loader.save()`
- `mcc/settings.yaml` — `index` key split into `user_index` / `tool_index`
- `tests/conftest.py` — env vars updated for split index names
- New file: `mcc/tool_db.py` — `ToolIndex` class
