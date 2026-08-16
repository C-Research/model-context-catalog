## ADDED Requirements

### Requirement: search_backend setting selects storage backend
The system SHALL provide a `search_backend` setting with allowed values `"elasticsearch"` and `"opensearch"`, defaulting to `"elasticsearch"`. This setting SHALL be read once at process/module load time to determine which storage backend `UsersIndex`, `KeysIndex`, and `ToolIndex` use. The backend SHALL NOT be switchable at runtime within a running process.

#### Scenario: Default backend is Elasticsearch
- **WHEN** `search_backend` is not set in configuration
- **THEN** the system uses Elasticsearch for all storage/search operations

#### Scenario: Explicit opensearch backend
- **WHEN** `search_backend` is set to `"opensearch"`
- **THEN** the system uses OpenSearch for all storage/search operations, and no Elasticsearch client is constructed

### Requirement: OSIndex base class
The system SHALL provide an `OSIndex` base class in `mcc/db/os.py`, structurally mirroring `mcc/db/es.py`'s `ESIndex`: an async context manager exposing `get(id)`, `mget(ids)`, `put(id, doc, refresh=True)`, `delete(id, refresh=True)`, `search(query, size=10000)`, `create()`, and `drop(ignore_unavailable=True)`, backed by an OpenSearch client (`opensearch-py`) rather than `AsyncElasticsearch`. Subclasses SHALL set `index` and `mapping` and implement `_make_client()`, matching `ESIndex`'s subclass contract.

#### Scenario: OSIndex CRUD parity with ESIndex
- **WHEN** a document is `put` into an `OSIndex` subclass and then retrieved with `get`
- **THEN** the retrieved document matches what was stored, with the same method signatures as the equivalent `ESIndex` operation

#### Scenario: OSIndex get on missing document returns None
- **WHEN** `get(id)` is called for an id that does not exist in the index
- **THEN** `OSIndex.get` returns `None`, matching `ESIndex.get`'s behavior

#### Scenario: OSIndex does not trigger Elasticsearch's product check
- **WHEN** `OSIndex` connects to an OpenSearch cluster
- **THEN** no `UnsupportedProductError` (or equivalent) is raised, because no `elasticsearch-py` client is used

### Requirement: OpenSearch client construction from settings
The system SHALL construct its OpenSearch client from an OpenSearch connection URL setting, extracting basic auth credentials and TLS verification options in the same spirit as `mcc/db/es.py::_client_kwargs()` does for Elasticsearch, adapted to `opensearch-py`'s client constructor kwargs.

#### Scenario: Basic auth extracted from URL
- **WHEN** the OpenSearch URL is `"https://user:pass@host:9200"`
- **THEN** the constructed client authenticates as `user`/`pass` and the URL passed to the client omits the userinfo

### Requirement: Optional dependency extra for the OpenSearch client
The system SHALL declare `opensearch` as an optional dependency extra in `pyproject.toml`, containing an async-capable `opensearch-py`. `elasticsearch[async]>=8,<9` SHALL remain a base (non-extra) dependency, unchanged, so that default installs (including the Dockerfile's plain `uv sync`) are unaffected. An Elasticsearch-only install SHALL NOT require `opensearch-py` to be installed, and `mcc/db/os.py` SHALL only be imported (by `mcc/db/__init__.py`'s dispatch) when `search_backend` selects OpenSearch.

#### Scenario: Elasticsearch-only install has no OpenSearch dependency
- **WHEN** MCC is installed without the `opensearch` extra and `search_backend` is `"elasticsearch"`
- **THEN** the process starts successfully without `opensearch-py` installed

### Requirement: Session store backed by Elasticsearch or OpenSearch
The system SHALL select `mcc/app.py`'s session-scoped context store (`_session_store`) backend using the same `search_backend` setting as `UsersIndex`/`KeysIndex`/`ToolIndex`: `key_value.aio.stores.elasticsearch.ElasticsearchStore` when `"elasticsearch"` (default, unchanged), `key_value.aio.stores.opensearch.OpenSearchStore` when `"opensearch"`. When `search_backend` is `"opensearch"`, no Elasticsearch client SHALL be constructed for the session store.

#### Scenario: OpenSearch backend requires no Elasticsearch cluster for session state
- **WHEN** `search_backend` is `"opensearch"`
- **THEN** `_session_store` is backed by `OpenSearchStore` using the same `AsyncOpenSearch` client construction as `OSIndex`, and no `AsyncElasticsearch` client is constructed anywhere in the process
