## Context

The MCC catalog loader is a dict subclass populated at startup by parsing YAML tool files. The `search` MCP tool currently iterates this dict with case-insensitive substring matching against tool name and description. There is no persistence layer for tools — they live only in memory.

Elasticsearch is already present as a dependency (used for the user store via `ESIndex` in `mcc/db.py`). The goal is to add a parallel `ToolIndex` that mirrors the in-memory loader state into ES, enabling full-text search on the tool catalog.

## Goals / Non-Goals

**Goals:**
- Add `ToolIndex(ESIndex)` for tool storage with CRUD returning `ToolModel`
- Add `Loader.save()` to push the full in-memory store to ES (drop + recreate + put all)
- Add `Loader.search()` delegating to ES multi-match
- Make `Loader.reload()` async so it calls `save()` after rebuilding the dict
- Call `loader.save()` at FastMCP startup (lifespan) and at CLI entrypoint
- Split ES settings `index` → `user_index` + `tool_index`

**Non-Goals:**
- Treating ES as the source of truth — YAML files remain authoritative
- Syncing tool mutations back to YAML
- Pagination or cursor-based search results
- Exposing additional ES query parameters via the MCP search tool (deferred)

## Decisions

### YAML files are the source of truth; ES is a disposable search store

ES is populated entirely from the in-memory loader on every startup and reload. `save()` drops and recreates the index each time, so stale tools (removed from YAML) never linger. There is no two-way sync.

*Alternative considered*: append-only puts (upsert). Rejected because deleted tools would persist in ES until manual cleanup.

### `load()` stays synchronous; `save()` is a separate async method

`load()` parses YAML files and builds the local dict — a purely CPU-bound, synchronous operation. `save()` is a distinct async method that pushes the dict to ES. This keeps the loading path simple and avoids forcing `asyncio.run()` at module level.

`reload()` becomes async since it must call `save()` after rebuilding the dict.

*Alternative considered*: making `load()` async and combining both steps. Rejected because it complicates module-level initialization and couples file parsing to network I/O.

### ES stores only search fields; loader dict is the source for full ToolModel data

ES documents contain only `{name, description, groups}` — the fields needed for matching and filtering. `ToolIndex.search()` returns document IDs (tool keys). `Loader.search()` resolves those keys against the local dict to return full `ToolModel` instances. No deserialization or callable re-resolution occurs on the read path — the in-memory loader is always authoritative for full tool details.

*Alternative considered*: storing full ToolModel data in ES and re-resolving `callable` from `fn` on read. Rejected because it adds unnecessary re-introspection overhead and duplicates data that is already in memory.

### Document ID is `tool.key`

`tool.key = ".".join(sorted(groups) + [name])` is already the unique identifier in the loader dict. Using it as the ES document ID keeps the two stores consistent and allows direct get-by-key lookups.

### ES index settings split from single `index` to `user_index` + `tool_index`

`settings.ELASTICSEARCH.INDEX` previously served only the user store. Adding a tool index requires a distinct setting. Both are namespaced under `elasticsearch:` in `settings.yaml`. This is a **breaking change** for any deployment using the env var `MCC_ELASTICSEARCH__INDEX`.

### Search uses `multi_match` with `fuzziness: AUTO`, boosting name over description

```json
{
  "multi_match": {
    "query": "<query>",
    "fields": ["name^2", "description"],
    "fuzziness": "AUTO"
  }
}
```

Name matches are boosted 2× over description matches. `fuzziness: AUTO` handles minor typos. Group filtering is applied as a `term` filter on the `groups` keyword field. Access filtering (can_access) is applied in Python after ES returns results, consistent with the existing pattern.

*Alternative considered*: `match_phrase` for stricter matching. Deferred — fuzziness is more useful for an AI-driven search tool. More advanced query params can be exposed to the MCP tool in a future change.

## Risks / Trade-offs

**Sync on every CLI invocation is eager** → `loader.save()` runs even for user management commands that don't touch tools. Risk: adds latency to CLI commands. Mitigation: ES writes are fast for small catalogs; acceptable for now.

**ES availability required at startup** → If ES is down, `loader.save()` will fail. Risk: app won't start. Mitigation: no change to current behavior (user store already requires ES at startup).

**Breaking settings rename** → `MCC_ELASTICSEARCH__INDEX` env var becomes invalid. Risk: silent misconfiguration if operators don't update. Mitigation: document clearly in the change; `user_index` has a sensible default (`mcc-users`).

**Stale tool index between restarts** → If the app crashes before `save()` completes, ES may reflect a previous state. Risk: search results lag behind YAML until next successful startup. Mitigation: acceptable given ES is a disposable cache.
