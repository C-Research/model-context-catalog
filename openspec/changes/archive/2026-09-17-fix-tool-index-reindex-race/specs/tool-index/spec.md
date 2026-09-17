## ADDED Requirements

### Requirement: ToolIndex backends expose a bulk write primitive
Each `ToolIndex` backend SHALL expose `async def bulk_put(self, actions: list[dict]) -> None`, a primitive CRUD operation alongside the existing `put`/`get`/`search`/`create`/`drop`. Each `action` is a `{_index, _id, _source}` dict, matching the shape both backends' bulk helpers expect. `bulk_put` SHALL write all given actions in a single bulk request, then refresh the index exactly once, so every document is readable at once rather than one at a time.

The Elasticsearch backend (`mcc/db/es.py`, `_ESIndexBase.bulk_put`) SHALL use `elasticsearch.helpers.async_bulk`. The OpenSearch backend (`mcc/db/os.py`, `_OSIndexBase.bulk_put`) SHALL use `opensearchpy.helpers.async_bulk`. Both accept the same action-dict shape, so callers (the `Loader`) do not need backend-specific logic to use `bulk_put`.

#### Scenario: bulk_put writes all actions in one request
- **WHEN** `bulk_put(actions)` is called with N actions
- **THEN** exactly one bulk write request is issued to the backend client, not N individual `put`/`index` calls

#### Scenario: bulk_put refreshes exactly once
- **WHEN** `bulk_put(actions)` is called with N actions
- **THEN** the index is refreshed exactly once after the bulk write, so the catalog is never observably partial between documents mid-write

#### Scenario: bulk_put produces the same documents as one-at-a-time indexing
- **WHEN** `bulk_put([{_id: tool_a.key, _source: doc_a}, {_id: tool_b.key, _source: doc_b}])` is called
- **THEN** the index contains the same stored documents, keyed by each action's `_id`, that calling `put(tool_a.key, doc_a)` then `put(tool_b.key, doc_b)` would have produced

#### Scenario: bulk_put works identically on OpenSearch
- **WHEN** `search_backend` is `"opensearch"` and `bulk_put(actions)` is called
- **THEN** the same bulk-write → single-refresh behavior applies, using `opensearchpy.helpers.async_bulk` in place of the Elasticsearch bulk helper
