## Context

MCC's storage layer is a thin wrapper around Elasticsearch: `mcc/esindex.py` defines a settings-agnostic `ESIndex` base class (async context manager over `AsyncElasticsearch`, with `get`/`put`/`mget`/`delete`/`search`/`create`/`drop`), and `mcc/db.py` defines three concrete indices on top of it — `UsersIndex`, `KeysIndex` (both pure CRUD) and `ToolIndex` (semantic tool search: BM25 `match` combined with native `knn` over a `dense_vector` field).

Some operators want to run MCC against AWS OpenSearch rather than standing up Elasticsearch. Two things make this non-trivial:

1. `elasticsearch-py` (v8) performs a client-side "product check" against the cluster and raises `UnsupportedProductError` when the server doesn't identify as genuine Elastic — so `AsyncElasticsearch` cannot be pointed at an OpenSearch cluster at all, even for plain CRUD.
2. OpenSearch's vector search is a different mapping type (`knn_vector`) and query DSL (the k-NN plugin's `knn` query clause), not `dense_vector` + native `knn`. There is no wire-compatible way to send the same query body to both.

This is a single-operator, deploy-time choice, not a runtime feature — a given MCC process talks to exactly one backend for its whole lifetime.

## Goals / Non-Goals

**Goals:**
- Let an operator run MCC entirely against OpenSearch by setting `search_backend: opensearch` in `settings.yaml`, with no other code changes.
- Keep the existing Elasticsearch path byte-for-byte behaviorally unchanged when `search_backend` is `elasticsearch` (the default).
- Keep `UsersIndex`/`KeysIndex` (pure CRUD) backend-selection simple, since they need almost no logic change between backends.
- Isolate the one place that genuinely differs — `ToolIndex`'s vector search mapping and query — into two independently readable, independently maintained classes.

**Non-Goals:**
- Running both backends simultaneously, migrating data between them, or switching backend at runtime.
- Normalizing or making comparable the relevance scores returned by the two backends. `min_score` stays a raw, backend-native threshold; callers of the `search` MCP tool already discover a workable threshold empirically per query, and that discovery process is unaffected — it just now also varies by backend.
- Automated test coverage for the OpenSearch path. `tests/conftest.py` continues to stand up a real Elasticsearch instance only; OpenSearch support is manually/best-effort verified.
- A unifying query-DSL abstraction over Elasticsearch's and OpenSearch's vector search. The two are different enough (field type, query clause shape, scoring engine) that an abstraction would either leak backend details anyway or force a lowest-common-denominator query that loses capability.

## Decisions

**1. Module layout: `mcc/db/` package — `base.py` (shared), `es.py`/`os.py` (fully self-contained per backend), `__init__.py` (glue).**
Revised during implementation: an earlier version of this design put ES-specific pieces across `mcc/esindex.py` + `mcc/db.py`, OS-specific pieces in a new `mcc/osindex.py`, and dispatched by conditionally assigning `UsersIndex`/`KeysIndex`'s *base class* from a variable (`class UsersIndex(_BASE): ...`) inside an `if settings.SEARCH_BACKEND == "opensearch": ...` block spanning most of `mcc/db.py`. That worked, but was hard to read (one large conditional block mixing both backends' code) and pyright cannot type-check a class whose base is a runtime-assigned variable (`reportGeneralTypeIssues: Argument to class must be a base class`). Final layout:
- `mcc/db/base.py` — backend-agnostic helpers used by both backends: the embedding model cache and `embed()`.
- `mcc/db/es.py` — every Elasticsearch-specific piece, fully self-contained: the generic index base class (formerly `mcc/esindex.py`), `_client_kwargs()`, and concrete `UsersIndex`/`KeysIndex`/`ToolIndex`/`session_store()` classes/functions, each a complete, independent definition (no cross-module inheritance).
- `mcc/db/os.py` — the OpenSearch mirror of `es.py`, same shape, same four names.
- `mcc/db/__init__.py` — the only place backend selection happens: imports either `mcc.db.es` or `mcc.db.os` based on `settings.SEARCH_BACKEND` and re-exports its `UsersIndex`/`KeysIndex`/`ToolIndex`/`session_store` under one name each. No conditional class construction, no dynamic base classes — just picking which already-fully-defined module to expose.

```python
# mcc/db/__init__.py
if settings.SEARCH_BACKEND == "opensearch":
    from mcc.db import os as _backend
else:
    from mcc.db import es as _backend

UsersIndex = _backend.UsersIndex
KeysIndex = _backend.KeysIndex
ToolIndex = _backend.ToolIndex
session_store = _backend.session_store
```
Callers (`mcc/auth/db.py`, `mcc/auth/keys.py`, `mcc/loader.py`, `mcc/app.py`) are unaffected — `from mcc.db import UsersIndex` etc. resolves identically whether `mcc.db` is a module or (now) a package. `mcc.db.os` (and `opensearch-py`) is only imported by `__init__.py` when that backend is selected, preserving the "Elasticsearch-only install never needs opensearch-py" property without needing a conditional import anywhere else.

Alternative considered (and rejected, for the reasons above): a factory function (`make_users_index()`) called at every construction site, and the original dynamic-base-class dispatch. Module-level re-export dispatch keeps construction call sites unchanged, avoids the pyright issue entirely, and reads as two independent, easily-diffable backend modules rather than one file with a backend switch running through the middle of it.

**2. `es.py`/`os.py` each duplicate the full CRUD surface, including `UsersIndex`/`KeysIndex`'s mapping dict.**
Each backend's generic index base class (`_ESIndexBase` in `es.py`, `_OSIndexBase` in `os.py`) is written narrowly against its own client library's response/exception shapes (e.g. `.options(ignore_status=404)` for `elasticsearch-py` vs. `params={"ignore": 404}` for `opensearch-py`) and cannot share a base without leaking one client's conventions into the other. Now that `UsersIndex`/`KeysIndex` are also fully independent per-module classes (not a shared class parameterized by base), their identical mapping dict (`username`/`email`/`groups`/`tools` as keyword, etc.) is duplicated verbatim in both files rather than imported from one. Given the CRUD surface and these mappings are small and rarely change, that duplication is judged cheaper than an abstraction that would need to paper over client differences — same tradeoff already accepted for `ToolIndex`'s two variants.

**3. `ToolIndex` as two fully separate classes, one per backend module, no shared query builder.**
- `mcc.db.es.ToolIndex` (existing, unchanged): `dense_vector` mapping, `{"query": {match...}, "knn": {...}}` combined search body.
- `mcc.db.os.ToolIndex` (new): `knn_vector` mapping (`method`/`engine` params appropriate for the k-NN plugin), and a search body using the k-NN plugin's `knn` query clause combined with a `match` text query inside a `bool`/`should`.

Both implement the same public contract (`put(tool) -> None`, `search(query, group=None) -> list[str]` per the existing `tool-index` spec) but the mapping dict and the query-building code inside `search`/`query` are independent, hand-written per backend. Alternative considered: parameterize a single `ToolIndex` class with an `if self.backend == ...` branch inside `query()`. Rejected per explicit preference — branching inside one method for a genuinely different DSL is harder to read than two small classes, and it invites accidental cross-contamination (e.g. a change meant for one engine silently affecting the other's code path).

**4. Client construction / URL handling.**
`mcc/db/es.py::_client_kwargs()` parses `ELASTICSEARCH_URL` to pull out `basic_auth` and `verify_certs` because `elasticsearch-py` handles the URL's userinfo/query-string unreliably. `opensearch-py`'s `AsyncOpenSearch` constructor has a similar but not identical kwarg shape (e.g. `http_auth` tuple, `use_ssl`/`verify_certs` as separate booleans rather than one query param). `mcc/db/os.py::_os_client_kwargs()` parses an OpenSearch connection URL/settings using the same approach, adapted to `opensearch-py`'s constructor. This is separate, backend-specific code, not shared with `_client_kwargs()`.

**5. Dependency packaging: `opensearch` extra only; Elasticsearch stays a base dependency.**
`pyproject.toml` gains `mcc[opensearch]` (`opensearch-py[async]`) as a new optional-dependency group. `elasticsearch[async]>=8,<9` is *not* moved into an extra — it stays a base (always-installed) dependency, because the Dockerfile and any other default install path (`uv sync` with no `--extra` flags) never requests extras, and this change's own migration plan promises existing deployments are unaffected with zero config changes. Making Elasticsearch extra-only would silently break that promise the moment someone did a plain install. Only one of the two client libraries needs to be importable at runtime for a given deployment; `mcc/db/os.py` is only imported by `mcc/db/__init__.py`'s dispatch when `search_backend` selects it, so an Elasticsearch-only (default) install never needs `opensearch-py` present.

**6. `min_score` semantics: unchanged, no cross-backend normalization.**
Explicitly decided against relative/normalized scoring (e.g. percentile-of-top-hit) to keep this change scoped to backend selection. `ToolIndex.query()`'s `min_score` parameter, `mcc/app.py`'s `search` tool docstring, and `mcc/loader.py`'s cache key logic are unchanged. Operators switching from Elasticsearch to OpenSearch may need to recalibrate whatever `min_score` values they'd settled on, same as they would when re-tuning against a different embedding model.

**7. Session store (`mcc/app.py::_session_store`) is a fourth name in the same per-backend modules, discovered during implementation.**
`mcc/app.py` constructs a second, independent Elasticsearch client for FastMCP's session-scoped context store (`key_value.aio.stores.elasticsearch.ElasticsearchStore`, index prefix `mcc-ctx`) — not part of `UsersIndex`/`KeysIndex`/`ToolIndex`, and not covered by the original proposal. Left untouched, `search_backend: opensearch` would still require a reachable Elasticsearch cluster for session state, which contradicts this change's premise (running MCC without a separate Elasticsearch cluster). The `key_value` library already ships `key_value.aio.stores.opensearch.OpenSearchStore` with an analogous constructor (`opensearch_client=`, `index_prefix=`). Rather than giving `app.py` its own dispatch, `session_store(index_prefix)` is a fourth function defined in both `mcc/db/es.py` and `mcc/db/os.py` (alongside `UsersIndex`/`KeysIndex`/`ToolIndex`) and re-exported by `mcc/db/__init__.py`'s dispatch like the other three; `app.py` just calls `session_store("mcc-ctx")` with no conditional of its own. This mirrors the existing precedent already in `app.py` for the event store (`RedisStore` imported only when `event_store.backend` selects redis), but keeps all backend-selection logic in one place (`mcc/db/__init__.py`) instead of spreading it across every consuming module.

## Risks / Trade-offs

- **[Risk] No automated test coverage for the OpenSearch path** → mitigated only by manual verification during implementation (start against a local OpenSearch instance, exercise `UsersIndex`/`KeysIndex` CRUD and `ToolIndex.search`/`.query` end to end). Regressions in the OpenSearch path could ship unnoticed until an operator hits them. Accepted per explicit scope decision; not solved by this change.
- **[Risk] Duplicated CRUD/query code drifts over time** (`mcc/db/es.py` vs `mcc/db/os.py`, and the two `ToolIndex`/`UsersIndex`/`KeysIndex` variants) → mitigated by keeping each surface small and by this design doc + spec scenarios serving as the shared contract both modules must satisfy, even though the code doesn't share a base class.
- **[Risk] Score-scale differences between backends surprise operators migrating from ES to OpenSearch** (a `min_score` tuned for Elasticsearch may filter too much/too little on OpenSearch) → accepted; out of scope per Non-Goals. Worth a docs callout when this ships.
- **[Trade-off] Two dependency extras instead of one bundled install** → slightly more packaging complexity, but avoids forcing every deployment to install both `elasticsearch-py` and `opensearch-py`.

## Migration Plan

No migration of existing deployments is required — `search_backend` defaults to `elasticsearch`, so existing installs are unaffected until an operator explicitly opts into `opensearch`. Operators wanting to switch:
1. Install `mcc[opensearch]`.
2. Set `search_backend: opensearch` and the OpenSearch connection URL in `settings.yaml`/`settings.local.yaml` (or via `MCC_SEARCH_BACKEND`/equivalent env var).
3. Point at an empty OpenSearch cluster — index creation (`create()`) runs the same as it does for Elasticsearch today; there is no data-migration path from an existing ES index to OpenSearch in this change.

Rollback is simply reverting `search_backend` to `elasticsearch` (or removing the override), since the two are independent, non-interacting code paths.

## Resolved Questions

- **`opensearch-py` async support**: `opensearch-py` ships a documented `AsyncOpenSearch` client, installed via the `opensearch-py[async]` extra. Its constructor kwarg shape mirrors the sync client closely enough to match `_client_kwargs()`'s existing approach (`host`/`port`, `http_auth` tuple, separate `use_ssl`/`verify_certs` booleans, rather than one URL). This is mature enough to use directly; no fallback or alternative transport needed. The `opensearch` extra (task 1.1) SHALL be `opensearch-py[async]`.
- **k-NN engine/method**: `nmslib` is OpenSearch's original, now less-favored k-NN engine; `faiss` and `lucene` are the current recommendations. Default to `faiss` (`method: {name: "hnsw", engine: "faiss", space_type: "cosinesimil"}`) for `ToolIndex(OSIndex)`'s `embedding` field, matching the Elasticsearch side's cosine `dense_vector`; fall back to `lucene` if the target OpenSearch/AWS OpenSearch Service version doesn't support `faiss`. Exact per-version engine availability on the operator's actual target cluster should still be confirmed manually during verification (task 5.1/5.2) — this resolves the engine *choice*, not cluster-specific availability.
