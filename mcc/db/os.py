"""OpenSearch-backed storage/search: index base class, client construction,
and the concrete `UsersIndex`/`KeysIndex`/`ToolIndex`/session store mcc uses
when `settings.SEARCH_BACKEND` is `"opensearch"`.

Only imported by `mcc.db`'s dispatch when that backend is selected, so an
Elasticsearch-only install never needs `opensearch-py` present.
"""

from time import time
from typing import ClassVar

from key_value.aio.stores.opensearch import OpenSearchStore
from opensearchpy import AsyncOpenSearch

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


class _OSIndexBase(IndexLifecycle):
    async def get(self, id: str) -> dict | None:
        """Return _source for the document, or None if not found."""
        resp = await self._client.get(index=self.index, id=id, params={"ignore": 404})
        return resp["_source"] if resp.get("found") else None

    async def mget(self, ids: list[str]) -> list[dict]:
        """Return _source dicts for the found subset of *ids* (missing skipped)."""
        if not ids:
            return []
        resp = await self._client.mget(index=self.index, body={"ids": ids})
        return [d["_source"] for d in resp["docs"] if d.get("found")]

    async def put(self, id: str, doc: dict, refresh: bool = True) -> None:
        """Index a document by id. Refreshes by default so it is readable at once."""
        await self._client.index(
            index=self.index,
            id=id,
            body=doc,
            params={"refresh": str(refresh).lower()},
        )

    async def delete(self, id: str, refresh: bool = True) -> None:
        """Delete a document by id. Raises NotFoundError if missing."""
        await self._client.delete(
            index=self.index, id=id, params={"refresh": str(refresh).lower()}
        )

    async def search(
        self,
        query: dict,
        limit: int = 10000,
        offset: int = 0,
        sort: list | None = None,
    ) -> list[dict]:
        """Run a raw OpenSearch query and return a list of _source dicts.

        `offset`/`limit` map to OpenSearch's `from`/`size`. `sort` is passed
        through verbatim (e.g. `[{"timestamp": "desc"}]`) when given,
        otherwise OpenSearch's default relevance ordering applies.
        """
        body: dict = {"query": query, "size": limit, "from": offset}
        if sort is not None:
            body["sort"] = sort
        resp = await self._client.search(index=self.index, body=body)
        return [hit["_source"] for hit in resp["hits"]["hits"]]

    async def create(self) -> None:
        """Create the index with the given mapping. No-op if it already exists."""
        if not await self._client.indices.exists(index=self.index):
            await self._client.indices.create(index=self.index, body=self.mapping)

    async def drop(self, ignore_unavailable: bool = True) -> None:
        """Delete the index."""
        await self._client.indices.delete(
            index=self.index,
            params={"ignore_unavailable": str(ignore_unavailable).lower()},
        )


def _os_client_kwargs() -> dict:
    """Build AsyncOpenSearch kwargs from OPENSEARCH_URL.

    Same URL convention as `mcc.db.es._client_kwargs()`: scheme/host/port/
    credentials in one value. Unlike AsyncElasticsearch, AsyncOpenSearch takes
    `use_ssl`/`verify_certs`/`http_auth` as separate constructor kwargs rather
    than accepting query-string options on the URL itself.
    """
    scheme, bare_url, verify_certs, basic_auth = parse_backend_url(
        settings.OPENSEARCH_URL
    )
    kwargs: dict = {"use_ssl": scheme == "https", "hosts": [bare_url]}
    if verify_certs is not None:
        kwargs["verify_certs"] = verify_certs
    if basic_auth is not None:
        kwargs["http_auth"] = basic_auth
    return kwargs


class IndexBase(_OSIndexBase):
    """mcc's OS index: connects to ``OPENSEARCH_URL`` and pings on enter."""

    ping_on_enter = True

    def _make_client(self) -> AsyncOpenSearch:
        return AsyncOpenSearch(**_os_client_kwargs())


class UsersIndex(IndexBase):
    index = settings.USER_INDEX
    mapping: ClassVar[dict] = USERS_MAPPING


class KeysIndex(IndexBase):
    index = settings.KEY_INDEX
    mapping: ClassVar[dict] = KEYS_MAPPING


class ToolIndex(IndexBase, ToolIndexMixin):
    """k-NN plugin `knn_vector` + query clause semantic search over `signature`."""

    index = settings.TOOL_INDEX
    mapping: ClassVar[dict] = {
        "settings": {"index.knn": True},
        "mappings": {
            "properties": {
                "signature": {"type": "text"},
                "groups": {"type": "keyword"},
                "embedding": {
                    "type": "knn_vector",
                    "dimension": settings.EMBEDDING_DIMS,
                    "method": {
                        "name": "hnsw",
                        "engine": "faiss",
                        "space_type": "cosinesimil",
                    },
                },
            }
        },
    }

    async def signatures(self) -> list[str]:
        """Return every indexed tool's signature, ordered by tool key."""
        resp = await self._client.search(
            index=self.index, body={"query": {"match_all": {}}, "size": 10000}
        )
        return sort_signatures(resp["hits"]["hits"])

    async def query(
        self,
        query: str,
        min_score: float | None = None,
        groups: list[str] | None = None,
    ) -> list[tuple[str, float]]:
        vector = await embed(query)
        bool_query: dict = {
            "should": [
                {"match": {"signature": {"query": query, "fuzziness": "AUTO"}}},
                {"knn": {"embedding": {"vector": vector, "k": 10}}},
            ]
        }
        if groups:
            bool_query["filter"] = [{"terms": {"groups": groups}}]
        body: dict = {"query": {"bool": bool_query}, "size": 10000}
        if min_score is not None:
            body["min_score"] = min_score
        t0 = time()
        resp = await self._client.search(index=self.index, body=body)
        hits = score_hits(resp["hits"]["hits"])
        log_query(query, hits, t0)
        return hits


def session_store(index_prefix: str) -> OpenSearchStore:
    """FastMCP session-scoped context store, backed by OpenSearch."""
    return OpenSearchStore(
        opensearch_client=AsyncOpenSearch(**_os_client_kwargs()),
        index_prefix=index_prefix,
    )
