## ADDED Requirements

### Requirement: ToolIndex class backed by Elasticsearch or OpenSearch
The system SHALL provide a `ToolIndex` class, exposed by `mcc/db/__init__.py`'s dispatch from either `mcc/db/es.py` or `mcc/db/os.py` based on `settings.SEARCH_BACKEND`. Both backends index the same three fields, unsplit: `signature` (the tool's full rendered signature block — name, description, and params — as one text field) as text/keyword-analyzed text, `groups` as keyword, and `embedding` (the vector of `signature`) as the backend's native vector type. There is no separate `name`/`description` split — search is not hybrid across independently-scored fields; the vector is computed over `signature` alone, same as the existing Elasticsearch implementation. When `search_backend` is `"elasticsearch"` (default), `ToolIndex` SHALL subclass `ESIndex` with `embedding` as `dense_vector`. When `search_backend` is `"opensearch"`, `ToolIndex` SHALL subclass `OSIndex` with `embedding` as `knn_vector`. In both cases the index name SHALL be read from `settings.TOOL_INDEX` and the document ID SHALL be `tool.key`. The two backend implementations SHALL be separate classes with independent mapping and query logic — no shared query-building code between them.

#### Scenario: ToolIndex uses configured tool index name
- **WHEN** `settings.TOOL_INDEX` is `"mcc-tools"`
- **THEN** all ToolIndex operations target the `mcc-tools` index, regardless of backend

#### Scenario: Elasticsearch backend selected by default
- **WHEN** `search_backend` is not set
- **THEN** `ToolIndex` subclasses `ESIndex` and uses the `dense_vector`-based mapping unchanged from before this change

#### Scenario: OpenSearch backend selected explicitly
- **WHEN** `search_backend` is `"opensearch"`
- **THEN** `ToolIndex` subclasses `OSIndex` and uses a `knn_vector`-based mapping via the OpenSearch k-NN plugin

### Requirement: UsersIndex class backed by Elasticsearch or OpenSearch
The system SHALL provide a `UsersIndex` class, exposed by `mcc/db/__init__.py`'s dispatch from either `mcc/db/es.py` (subclassing `ESIndex`, default) or `mcc/db/os.py` (subclassing `OSIndex`) based on `settings.SEARCH_BACKEND`. Its index name SHALL be read from `settings.USER_INDEX` in either case. `UsersIndex`'s CRUD behavior (`get`/`put`/`mget`/`delete`) SHALL be identical between backends since it performs no backend-specific search/vector logic.

#### Scenario: UsersIndex reads user_index setting regardless of backend
- **WHEN** `settings.USER_INDEX` is `"mcc-users"`
- **THEN** `UsersIndex` targets the `mcc-users` index whether backed by Elasticsearch or OpenSearch

#### Scenario: UsersIndex CRUD parity across backends
- **WHEN** a user document is put and then retrieved via `UsersIndex`, first with `search_backend: elasticsearch` and then with `search_backend: opensearch`
- **THEN** both backends return the same stored document for the same operations

### Requirement: ToolIndex stores only search fields
`ToolIndex` SHALL expose `put(tool: ToolModel) -> None`. `put` SHALL store only `{name, description, groups}` — no `fn`, `params`, or `callable`. The document ID SHALL be `tool.key`.

#### Scenario: put stores only search-relevant fields
- **WHEN** a `ToolModel` is put into the index
- **THEN** the stored ES document contains only `name`, `description`, and `groups`

### Requirement: ToolIndex search returns keys
`ToolIndex` SHALL expose `search(query: str, group: str | None = None) -> list[str]` returning document IDs (tool keys). The query SHALL be matched against `name` (boosted 2×) and `description` using a `multi_match` query with `fuzziness: AUTO`. When `group` is provided, results SHALL be filtered to tools whose `groups` field contains that value.

#### Scenario: Search returns matching tool keys
- **WHEN** query is `"weather"` and a tool with key `"ops.get_weather"` is indexed
- **THEN** `"ops.get_weather"` is included in the returned key list

#### Scenario: Search matches on description
- **WHEN** query text appears only in a tool's description, not its name
- **THEN** that tool's key is included in results

#### Scenario: Fuzzy search tolerates minor typos
- **WHEN** query is `"wether"` (typo) and a tool named `get_weather` is indexed
- **THEN** that tool's key is included in results

#### Scenario: Group filter restricts results
- **WHEN** `group="ops"` is provided and two tools exist with groups `["ops"]` and `["finance"]`
- **THEN** only the `ops` tool's key is returned

#### Scenario: Empty results return empty list
- **WHEN** the query matches no indexed tools
- **THEN** `search()` returns an empty list

### Requirement: Settings split for user and tool indices
The `elasticsearch` settings block SHALL use `user_index` for the user store index name and `tool_index` for the tool store index name, replacing the previous single `index` key. Default values SHALL be `mcc-users` and `mcc-tools` respectively.

#### Scenario: UsersIndex reads user_index setting
- **WHEN** `settings.ELASTICSEARCH.USER_INDEX` is `"mcc-users"`
- **THEN** `UsersIndex` targets the `mcc-users` ES index

#### Scenario: ToolIndex reads tool_index setting
- **WHEN** `settings.ELASTICSEARCH.TOOL_INDEX` is `"mcc-tools"`
- **THEN** `ToolIndex` targets the `mcc-tools` ES index

### Requirement: ToolIndex search DSL is backend-specific
Regardless of backend, `ToolIndex` SHALL expose the same public contract: `put`/`index_tool(tool: ToolModel) -> None` storing `{signature, groups, embedding}` (embedding computed over `signature`, no other fields), and `query(query: str, min_score: Optional[float] = None) -> list[tuple[str, float]]` returning tool keys ranked by relevance to a semantic/text query against `signature`. There is no separate `group` filter parameter on `query()`; narrowing by group is a query-text convention (callers include the group name in the natural-language query), unchanged by this feature. The Elasticsearch-backed implementation SHALL use a combined BM25 `match` and native `knn` query against a `dense_vector` field, unchanged from before this change. The OpenSearch-backed implementation SHALL use the OpenSearch k-NN plugin's query clause against a `knn_vector` field, combined with a text match query on `signature`, as an independent implementation of the same contract.

#### Scenario: Search returns matching tool keys on Elasticsearch
- **WHEN** `search_backend` is `"elasticsearch"`, query is `"weather"`, and a tool with key `"ops.get_weather"` is indexed
- **THEN** `"ops.get_weather"` is included in the returned key list

#### Scenario: Search returns matching tool keys on OpenSearch
- **WHEN** `search_backend` is `"opensearch"`, query is `"weather"`, and a tool with key `"ops.get_weather"` is indexed
- **THEN** `"ops.get_weather"` is included in the returned key list

#### Scenario: min_score is passed through without cross-backend normalization
- **WHEN** a caller supplies `min_score` to `ToolIndex.query()`
- **THEN** the value is passed to the backend's native scoring/filtering mechanism as-is, with no rescaling based on which backend is active

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
