"""Elasticsearch-backed storage/search: index base class, client construction,
and the concrete `UsersIndex`/`KeysIndex`/`ToolIndex`/session store mcc uses
when `settings.SEARCH_BACKEND` is `"elasticsearch"` (the default).
"""

from time import time
from typing import ClassVar

from elasticsearch import AsyncElasticsearch
from key_value.aio.stores.elasticsearch import ElasticsearchStore

from mcc.db.base import (
    KEYS_MAPPING,
    USERS_MAPPING,
    IndexLifecycle,
    ToolIndexMixin,
    embed,
    log_query,
    parse_backend_url,
    score_hits,
    sort_signatures,
)
from mcc.settings import settings


class _ESIndexBase(IndexLifecycle):
    async def get(self, id: str) -> dict | None:
        """Return _source for the document, or None if not found."""
        resp = await self._client.options(ignore_status=404).get(
            index=self.index, id=id
        )
        return resp["_source"] if resp.get("found") else None

    async def mget(self, ids: list[str]) -> list[dict]:
        """Return _source dicts for the found subset of *ids* (missing skipped)."""
        if not ids:
            return []
        resp = await self._client.mget(index=self.index, ids=ids)
        return [d["_source"] for d in resp["docs"] if d.get("found")]

    async def put(self, id: str, doc: dict, refresh: bool = True) -> None:
        """Index a document by id. Refreshes by default so it is readable at once."""
        await self._client.index(index=self.index, id=id, document=doc, refresh=refresh)

    async def delete(self, id: str, refresh: bool = True) -> None:
        """Delete a document by id. Raises NotFoundError if missing."""
        await self._client.delete(index=self.index, id=id, refresh=refresh)

    async def search(
        self,
        query: dict,
        limit: int = 10000,
        offset: int = 0,
        sort: list | None = None,
    ) -> list[dict]:
        """Run a raw ES query and return a list of _source dicts.

        `offset`/`limit` map to ES's `from`/`size`. `sort` is passed through
        verbatim (e.g. `[{"timestamp": "desc"}]`) when given, otherwise ES's
        default relevance ordering applies.
        """
        kwargs: dict = {"query": query, "size": limit, "from_": offset}
        if sort is not None:
            kwargs["sort"] = sort
        resp = await self._client.search(index=self.index, **kwargs)
        return [hit["_source"] for hit in resp["hits"]["hits"]]

    async def create(self) -> None:
        """Create the index with the given mapping. No-op if it already exists."""
        if not await self._client.indices.exists(index=self.index):
            await self._client.indices.create(index=self.index, **self.mapping)

    async def drop(self, ignore_unavailable: bool = True) -> None:
        """Delete the index."""
        await self._client.indices.delete(
            index=self.index, ignore_unavailable=ignore_unavailable
        )


def _client_kwargs() -> dict:
    """Build AsyncElasticsearch kwargs from ELASTICSEARCH_URL.

    The URL covers scheme/host/port/credentials in one value, e.g.
    "https://user:pass@host:9200?verify_certs=false".
    """
    _scheme, bare_url, verify_certs, basic_auth = parse_backend_url(
        settings.ELASTICSEARCH_URL
    )
    kwargs: dict = {"hosts": [bare_url]}
    if verify_certs is not None:
        kwargs["verify_certs"] = verify_certs
    if basic_auth is not None:
        kwargs["basic_auth"] = basic_auth
    return kwargs


class IndexBase(_ESIndexBase):
    """mcc's ES index: connects to ``ELASTICSEARCH_URL`` and pings on enter."""

    ping_on_enter = True

    def _make_client(self) -> AsyncElasticsearch:
        return AsyncElasticsearch(**_client_kwargs())


class UsersIndex(IndexBase):
    index = settings.USER_INDEX
    mapping: ClassVar[dict] = USERS_MAPPING


class KeysIndex(IndexBase):
    index = settings.KEY_INDEX
    mapping: ClassVar[dict] = KEYS_MAPPING


class ToolIndex(IndexBase, ToolIndexMixin):
    """Native `knn` + `dense_vector` semantic search over `signature`."""

    index = settings.TOOL_INDEX
    mapping: ClassVar[dict] = {
        "mappings": {
            "properties": {
                "signature": {"type": "text"},
                "groups": {"type": "keyword"},
                "embedding": {
                    "type": "dense_vector",
                    "dims": settings.EMBEDDING_DIMS,
                    "index": True,
                    "similarity": "cosine",
                },
            }
        }
    }

    async def signatures(self) -> list[str]:
        """Return every indexed tool's signature, ordered by tool key.

        Reads straight from ES so callers get the catalog regardless of whether
        the in-memory loader is populated (it is not in an exec subprocess)."""
        resp = await self._client.search(
            index=self.index, query={"match_all": {}}, size=10000
        )
        return sort_signatures(resp["hits"]["hits"])

    async def query(
        self,
        query: str,
        min_score: float | None = None,
        groups: list[str] | None = None,
    ) -> list[tuple[str, float]]:
        vector = await embed(query)
        text_query: dict = {
            "match": {"signature": {"query": query, "fuzziness": "AUTO"}}
        }
        knn: dict = {
            "field": "embedding",
            "query_vector": vector,
            "k": 10,
            "num_candidates": 50,
        }
        if groups:
            groups_filter = {"terms": {"groups": groups}}
            text_query = {"bool": {"must": [text_query], "filter": [groups_filter]}}
            knn["filter"] = groups_filter
        kwargs: dict = {"query": text_query, "knn": knn, "size": 10000}
        if min_score is not None:
            kwargs["min_score"] = min_score
        t0 = time()
        resp = await self._client.search(index=self.index, **kwargs)
        hits = score_hits(resp["hits"]["hits"])
        log_query(query, hits, t0)
        return hits


def session_store(index_prefix: str) -> ElasticsearchStore:
    """FastMCP session-scoped context store, backed by Elasticsearch."""
    return ElasticsearchStore(
        elasticsearch_client=AsyncElasticsearch(**_client_kwargs()),
        index_prefix=index_prefix,
    )
