## 1. Dependencies and settings plumbing

- [x] 1.1 Add an `opensearch` optional dependency extra (`opensearch-py[async]`) to `pyproject.toml`. `elasticsearch[async]>=8,<9` stays a base dependency (not moved to an extra) so default installs — including the Dockerfile's plain `uv sync --frozen --no-dev` — are unaffected, matching the "no migration needed" guarantee
- [x] 1.2 Add `search_backend` setting to `mcc/settings.yaml` (default `"elasticsearch"`) and an OpenSearch connection URL setting alongside the existing `elasticsearch_url`
- [x] 1.3 Update `uv.lock` for the new extras
- [x] 1.4 Add a "Search backend" section to `docs/getting-started/configuration.md`, alongside the existing "Elasticsearch" settings-reference section, documenting `search_backend` (default `elasticsearch`) and the new OpenSearch connection URL setting, with an example `settings.local.yaml` snippet for switching to OpenSearch

## 2. OSIndex base class

- [x] 2.1 Create `mcc/db/os.py` with an `OSIndex` base class mirroring `mcc/db/es.py`'s `ESIndex`: async context manager, `get`/`mget`/`put`/`delete`/`search`/`create`/`drop`, `index`/`mapping` class attributes, `_make_client()` seam, `ping_on_enter` support. (Superseded a first pass that split this across top-level `mcc/esindex.py`/`mcc/osindex.py`/`mcc/db.py` — reorganized into the `mcc/db/` package per the mid-implementation layout refactor; see design.md Decision 1.)
- [x] 2.2 Handle `opensearch-py`'s response/404 conventions in `get`/`mget` so behavior matches `ESIndex` (e.g. `get` on a missing id returns `None`)
- [x] 2.3 Add an OpenSearch equivalent of `mcc/db/es.py::_client_kwargs()` (`mcc/db/os.py::_os_client_kwargs()`, parsing the OpenSearch URL setting for basic auth / TLS verification, adapted to `AsyncOpenSearch`'s constructor kwargs)

## 3. Backend selection for UsersIndex, KeysIndex, and the session store

- [x] 3.1 In `mcc/db/__init__.py`, add module-level dispatch on `settings.SEARCH_BACKEND` selecting the `mcc.db.es` or `mcc.db.os` module and re-exporting its `UsersIndex`/`KeysIndex` (each a fully independent class per module, not a shared class with a dynamic base — avoids pyright's `reportGeneralTypeIssues` on runtime-assigned base classes)
- [x] 3.2 Verify `UsersIndex`'s mapping (`username`/`email`/`groups`/`tools` as keyword) is expressible identically on both backends
- [x] 3.3 Verify `KeysIndex`'s mapping (`prefix`/`hash`/`username` as keyword, `expires_at`/`created_at` as date) is expressible identically on both backends
- [x] 3.4 Confirm no other code constructs `AsyncElasticsearch`/`ESIndex` directly for these two indices (grep `mcc/auth/db.py`, `mcc/auth/keys.py`) — all construction should go through `UsersIndex()`/`KeysIndex()`
- [x] 3.5 Add `session_store(index_prefix)` as a fourth dispatched name in `mcc/db/es.py`/`mcc/db/os.py` (building `key_value.aio.stores.elasticsearch.ElasticsearchStore`/`key_value.aio.stores.opensearch.OpenSearchStore` respectively) and re-export it from `mcc/db/__init__.py`; `mcc/app.py` calls `session_store("mcc-ctx")` with no dispatch of its own
- [x] 3.6 Confirm that with `search_backend: opensearch`, no `AsyncElasticsearch` client is constructed anywhere in the process (grep for `AsyncElasticsearch` outside `mcc/db/es.py`)

## 4. ToolIndex OpenSearch variant

- [x] 4.1 Add a `knn_vector` mapping for `embedding` on the OpenSearch-backed `ToolIndex` (`method: hnsw`, `engine: faiss`, `space_type: cosinesimil`, falling back to `engine: lucene` if the target cluster lacks `faiss`), alongside `signature` (text) and `groups` (keyword) — no separate name/description fields
- [x] 4.2 Implement `index_tool`/`put` for the OpenSearch-backed `ToolIndex`, storing the same fields (`signature`, `groups`, `embedding`) as the Elasticsearch variant
- [x] 4.3 Implement `query`/`search` for the OpenSearch-backed `ToolIndex` using the k-NN plugin's query clause combined with a text match query, preserving the existing public contract (`query(query, min_score=None) -> list[tuple[str, float]]`, `signatures()`)
- [x] 4.4 `mcc/db/__init__.py`'s dispatch (task 3.1) also re-exports `ToolIndex` from whichever backend module is selected, without altering the existing Elasticsearch implementation
- [x] 4.5 Confirm `min_score` is passed through to each backend's native query/filter mechanism unchanged, with no normalization between backends

## 5. Verification (manual/best-effort, no automated OpenSearch tests)

- [x] 5.1 Add `docker-compose.opensearch.yaml` alongside the existing `docker-compose.yml`, standing up a local single-node OpenSearch instance (healthcheck, exposed port, persisted volume, mirroring the existing `elasticsearch` service shape) plus an `mcc` service configured with `MCC_SEARCH_BACKEND=opensearch` and the OpenSearch connection URL, for use in the manual verification below
- [x] 5.2 Run the `docker-compose.opensearch.yaml` stack and manually exercise `UsersIndex` and `KeysIndex` CRUD (create/get/put/mget/delete) with `search_backend: opensearch`
- [x] 5.3 Manually exercise `ToolIndex.index_tool` + `.query()`/`.signatures()` against the local OpenSearch instance and confirm semantic search returns expected tool keys
- [x] 5.4 Confirm the existing Elasticsearch-backed test suite (`uv run pytest tests/`) still passes unchanged with `search_backend` defaulting to `"elasticsearch"`
- [x] 5.5 Confirm an Elasticsearch-only install (without the `opensearch` extra) still starts and runs correctly, i.e. `mcc/db/os.py` is not imported on that path
- [x] 5.6 Run `ruff` and `pyright` per `AGENTS.md` across the new/changed files. `uv run pyright mcc/db/` and `uv run ruff check mcc/db/` are both clean (fixed 8 `UP045`/`RUF012` findings — `Optional[X]` → `X | None`, `mapping` class attrs annotated `ClassVar[dict]`). Repo-wide `ruff check .`/`pyright` still carry pre-existing debt outside `mcc/db/` (unchanged baseline, out of scope for this change).
