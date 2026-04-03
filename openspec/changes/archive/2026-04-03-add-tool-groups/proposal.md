## Why

Tools in the catalog have no organizational structure, making it difficult to scope searches or reason about which tools belong to a domain. Groups let users partition tools by concern and filter searches to a relevant subset.

## What Changes

- **BREAKING**: YAML tool files must now be a dict with `tools` key (list) instead of a bare list. An optional `group` key sets the group for all tools in the file.
- `search` MCP tool gains an optional `group` parameter; when provided, only tools in that group are matched.
- Registry entries gain a `group` field (`str | None`).
- Loader rejects the old flat-list format at startup.

## Capabilities

### New Capabilities
- `tool-groups`: Group assignment for tools via file-level YAML key; group filtering in search.

### Modified Capabilities
- `tool-catalog`: YAML format changes from flat list to dict wrapper — this is a spec-level requirement change.
- `catalog-loader`: Loader must parse the new dict format and propagate group to each tool entry.
- `search-tool`: Search gains an optional `group` filter parameter.

## Impact

- `mcc/loader.py` — `load_file` and `Loader.register` updated for new format and group propagation
- `mcc/app.py` — `search()` signature and logic updated
- `tools.yaml` — must be migrated to new dict-wrapper format
- Registry entry dict gains `"group"` key — any consumers reading registry entries directly are affected
