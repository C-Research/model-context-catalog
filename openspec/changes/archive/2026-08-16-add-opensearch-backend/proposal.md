## Why

MCC's storage/search layer is hard-coupled to Elasticsearch (`mcc/esindex.py`, `mcc/db.py`), but some deployments run AWS OpenSearch instead — Elastic's client rejects those clusters outright (`UnsupportedProductError`) and OpenSearch's vector search uses a different mapping type and query DSL. Supporting OpenSearch as an alternative backend lets those deployments adopt MCC without standing up a separate Elasticsearch cluster.

## What Changes

- Add a `search_backend` setting (`elasticsearch` | `opensearch`, default `elasticsearch`) that selects the storage/search implementation at deploy time. Not switchable at runtime; a given process talks to exactly one backend.
- Reorganize storage/search code into a `mcc/db/` package: `mcc/db/base.py` (backend-agnostic embedding helpers), `mcc/db/es.py` (every Elasticsearch-specific piece — index base class, client construction, `UsersIndex`/`KeysIndex`/`ToolIndex`/`session_store`), `mcc/db/os.py` (the OpenSearch mirror, built on `opensearch-py` instead of `elasticsearch-py`), and `mcc/db/__init__.py` (the only place backend selection happens — imports `mcc.db.es` or `mcc.db.os` based on `settings.SEARCH_BACKEND` and re-exports its four names). `mcc/esindex.py`/`mcc/osindex.py`/the old single-file `mcc/db.py` are removed; existing `from mcc.db import UsersIndex` (etc.) call sites are unaffected.
- `UsersIndex` and `KeysIndex` are fully independent classes in `es.py`/`os.py` (not a shared class parameterized by base). Both are pure CRUD, so the OpenSearch variant is close to a drop-in aside from its client library's conventions.
- `ToolIndex` (semantic tool search) gets two separate, independently-maintained implementations rather than a shared query abstraction:
  - `ToolIndex(ESIndex)`: existing `dense_vector` mapping + combined `match`+native `knn` query (unchanged).
  - `ToolIndex(OSIndex)`: new `knn_vector` mapping + OpenSearch k-NN plugin query DSL.
- Add an `mcc[opensearch]` optional dependency extra in `pyproject.toml`. `elasticsearch[async]` remains a base (non-extra) dependency, so default installs — including the Dockerfile's `uv sync` — are unaffected; only OpenSearch is opt-in.
- `min_score` on `ToolIndex.query()` / the `search` MCP tool remains a raw, backend-native score threshold with no cross-backend normalization — OpenSearch and Elasticsearch may produce different absolute score scales for the same query, and callers are expected to discover the right threshold empirically per backend, same as today.
- `mcc/app.py`'s session-scoped context store (`_session_store`, backing `Ctx` state via FastMCP's `key_value` session storage) also becomes backend-selectable via the same `settings.SEARCH_BACKEND` dispatch — `key_value.aio.stores.elasticsearch.ElasticsearchStore` (unchanged) or `key_value.aio.stores.opensearch.OpenSearchStore` (new), constructed the same way `UsersIndex`/`KeysIndex`/`ToolIndex` pick their client. Discovered during implementation: without this, `search_backend: opensearch` would still require a reachable Elasticsearch cluster just for session state, undercutting the change's own goal of not needing a separate Elasticsearch cluster.

## Capabilities

### New Capabilities
- `opensearch-backend`: OpenSearch as a selectable, alternative storage/search backend for users, API keys, and semantic tool search, chosen via `search_backend` setting.

### Modified Capabilities
- `tool-index`: `ToolIndex` and `UsersIndex` become backend-selectable (`ESIndex`-backed or `OSIndex`-backed) based on `settings.SEARCH_BACKEND`, rather than unconditionally subclassing `ESIndex`.
- `api-key-auth`: `KeysIndex` becomes backend-selectable the same way.

## Impact

- **Code**: new `mcc/db/` package (`base.py`, `es.py`, `os.py`, `__init__.py`) replacing `mcc/esindex.py`/`mcc/osindex.py`/`mcc/db.py`; `mcc/app.py` (now calls `session_store()` from `mcc.db`, no dispatch of its own); `mcc/settings.py`/`mcc/settings.yaml` (new `search_backend` setting); `pyproject.toml` (new `opensearch` extra).
- **Dependencies**: adds `opensearch-py` (async variant) as an optional dependency; no change to the default (Elasticsearch) install.
- **Tests**: no new automated coverage — `tests/` remains Elasticsearch-only (real ES instance via `tests/conftest.py`); the OpenSearch path is best-effort/manually verified.
- **Docs/config**: `mcc/settings.yaml` gains `search_backend` (default `elasticsearch`) and an OpenSearch connection URL setting alongside the existing `elasticsearch_url`; `docs/getting-started/configuration.md` gains a "Search backend" section documenting both, alongside the existing "Elasticsearch" section.
- **Local dev**: new `docker-compose.opensearch.yaml` alongside the existing `docker-compose.yml`, standing up a local OpenSearch instance for manual verification of the OpenSearch path.
