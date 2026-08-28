"""OpenSearch-backed storage/search: index base class, client construction,
and the concrete `UsersIndex`/`KeysIndex`/`ToolIndex`/session store mcc uses
when `settings.SEARCH_BACKEND` is `"opensearch"`.

Only imported by `mcc.db`'s dispatch when that backend is selected, so an
Elasticsearch-only install never needs `opensearch-py` present.
"""

from time import time
from typing import ClassVar
from urllib.parse import parse_qs, urlparse, urlunparse

from key_value.aio.stores.opensearch import OpenSearchStore
from opensearchpy import AsyncOpenSearch

from mcc.db.base import embed
from mcc.models import ToolModel
from mcc.settings import logger, settings


class _OSIndexBase:
    """Async OpenSearch index with scoped document operations.

    Used as an async context manager::

        async with SomeIndex() as idx:
            await idx.put("id", {...})

    Subclasses MUST set ``index`` / ``mapping`` and implement ``_make_client``.
    Set ``ping_on_enter = True`` to verify connectivity (``client.info()``) on
    enter — fail-fast at the cost of a round-trip.
    """

    index = "index"
    mapping: ClassVar[dict] = {}
    ping_on_enter: bool = False

    def _make_client(self) -> AsyncOpenSearch:
        """Return the OpenSearch client this index operates against.

        Override in a subclass to bind the index to a specific cluster/settings.
        """
        raise NotImplementedError(
            f"{type(self).__name__} must implement _make_client()"
        )

    async def __aenter__(self):
        self._client = self._make_client()
        if self.ping_on_enter:
            await self._client.info()
        return self

    async def __aexit__(self, *_exc) -> None:
        await self._client.close()

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

    async def search(self, query: dict, size: int = 10000) -> list[dict]:
        """Run a raw OpenSearch query and return a list of _source dicts."""
        resp = await self._client.search(
            index=self.index, body={"query": query, "size": size}
        )
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
    url = settings.OPENSEARCH_URL
    parsed = urlparse(url)
    kwargs: dict = {"use_ssl": parsed.scheme == "https"}

    params = parse_qs(parsed.query)
    if "verify_certs" in params:
        kwargs["verify_certs"] = params["verify_certs"][0].lower() not in (
            "false",
            "0",
            "no",
        )

    if parsed.username:
        kwargs["http_auth"] = (parsed.username, parsed.password or "")

    netloc = parsed.hostname or ""
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    kwargs["hosts"] = [urlunparse(parsed._replace(netloc=netloc, query=""))]
    return kwargs


class IndexBase(_OSIndexBase):
    """mcc's OS index: connects to ``OPENSEARCH_URL`` and pings on enter."""

    ping_on_enter = True

    def _make_client(self) -> AsyncOpenSearch:
        return AsyncOpenSearch(**_os_client_kwargs())


class UsersIndex(IndexBase):
    index = settings.USER_INDEX
    mapping: ClassVar[dict] = {
        "mappings": {
            "properties": {
                "username": {"type": "keyword"},
                "email": {"type": "keyword"},
                "groups": {"type": "keyword"},
                "tools": {"type": "keyword"},
            }
        }
    }


class KeysIndex(IndexBase):
    index = settings.KEY_INDEX
    mapping: ClassVar[dict] = {
        "mappings": {
            "properties": {
                "prefix": {"type": "keyword"},
                "hash": {"type": "keyword"},
                "username": {"type": "keyword"},
                "expires_at": {"type": "date"},
                "created_at": {"type": "date"},
            }
        }
    }


class ToolIndex(IndexBase):
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
        hits = sorted(
            (hit["_id"], hit["_source"]["signature"]) for hit in resp["hits"]["hits"]
        )
        return [sig for _, sig in hits]

    async def index_tool(self, tool: ToolModel) -> None:
        await self.put(
            tool.key,
            {
                "signature": tool.signature,
                "groups": tool.groups,
                "embedding": await embed(tool.signature),
            },
        )

    async def query(
        self, query: str, min_score: float | None = None
    ) -> list[tuple[str, float]]:
        vector = await embed(query)
        body: dict = {
            "query": {
                "bool": {
                    "should": [
                        {"match": {"signature": {"query": query, "fuzziness": "AUTO"}}},
                        {"knn": {"embedding": {"vector": vector, "k": 10}}},
                    ]
                }
            },
            "size": 10000,
        }
        if min_score is not None:
            body["min_score"] = min_score
        t0 = time()
        resp = await self._client.search(index=self.index, body=body)
        hits = [(hit["_id"], hit["_score"]) for hit in resp["hits"]["hits"]]
        logger.debug(
            "search %r → %d hits in %dms", query, len(hits), (time() - t0) * 1000
        )
        return hits


def session_store(index_prefix: str) -> OpenSearchStore:
    """FastMCP session-scoped context store, backed by OpenSearch."""
    return OpenSearchStore(
        opensearch_client=AsyncOpenSearch(**_os_client_kwargs()),
        index_prefix=index_prefix,
    )
