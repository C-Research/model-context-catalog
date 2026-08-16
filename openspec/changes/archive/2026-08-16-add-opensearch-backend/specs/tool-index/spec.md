## MODIFIED Requirements

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

## ADDED Requirements

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
