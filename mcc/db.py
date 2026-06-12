import asyncio
from time import time
from typing import Optional
from urllib.parse import parse_qs, urlparse, urlunparse

from elasticsearch import AsyncElasticsearch
from fastembed import TextEmbedding

from mcc.models import ToolModel
from mcc.settings import logger, settings

_embedding_model: Optional[TextEmbedding] = None


def _get_model() -> TextEmbedding:
    global _embedding_model
    if _embedding_model is None:
        model_name = settings.EMBEDDING_MODEL
        logger.info("Loading embedding model %s...", model_name)
        t0 = time()
        _embedding_model = TextEmbedding(model_name)
        logger.info("Embedding model loaded in %dms", (time() - t0) * 1000)
    return _embedding_model


async def embed(text: str) -> list[float]:
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, lambda: next(iter(_get_model().embed([text])))
    )
    return result.tolist()


def _client_kwargs() -> dict:
    """Build AsyncElasticsearch kwargs from ELASTICSEARCH_URL.

    The URL covers scheme/host/port/credentials in one value, e.g.
    "https://user:pass@host:9200?verify_certs=false". The ES client ignores the
    query string and is unreliable about userinfo, so verify_certs and any
    user:password are extracted here and passed explicitly; the URL handed to
    the client is stripped of both.
    """
    url = settings.ELASTICSEARCH_URL
    parsed = urlparse(url)
    kwargs: dict = {}

    params = parse_qs(parsed.query)
    if "verify_certs" in params:
        kwargs["verify_certs"] = params["verify_certs"][0].lower() not in (
            "false",
            "0",
            "no",
        )

    if parsed.username:
        kwargs["basic_auth"] = (parsed.username, parsed.password or "")

    # Rebuild the netloc without userinfo, and drop the query string.
    netloc = parsed.hostname or ""
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    kwargs["hosts"] = [urlunparse(parsed._replace(netloc=netloc, query=""))]
    return kwargs


class ESIndex:
    """Async Elasticsearch index with scoped operations."""

    index = "index"
    mapping = {}

    async def __aenter__(self):
        self._client = AsyncElasticsearch(**_client_kwargs())
        await self._client.info()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._client.close()

    async def get(self, id: str) -> Optional[dict]:
        """Return _source for the document, or None if not found."""
        resp = await self._client.options(ignore_status=404).get(
            index=self.index, id=id
        )
        return resp["_source"] if resp.get("found") else None

    async def put(self, id: str, doc: dict, refresh: bool = True) -> None:
        """Index a document by id."""
        await self._client.index(index=self.index, id=id, document=doc, refresh=refresh)

    async def delete(self, id: str, refresh: bool = True) -> None:
        """Delete a document by id. Raises NotFoundError if missing."""
        await self._client.delete(index=self.index, id=id, refresh=refresh)

    async def search(self, query: dict, size: int = 10000) -> list[dict]:
        """Run a raw ES query and return a list of _source dicts."""
        resp = await self._client.search(index=self.index, query=query, size=size)
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


class UsersIndex(ESIndex):
    index = settings.ELASTICSEARCH__USER_INDEX
    mapping = {
        "mappings": {
            "properties": {
                "username": {"type": "keyword"},
                "email": {"type": "keyword"},
                "groups": {"type": "keyword"},
                "tools": {"type": "keyword"},
            }
        }
    }


class ToolIndex(ESIndex):
    index = settings.ELASTICSEARCH__TOOL_INDEX
    mapping = {
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
        self, query: str, min_score: Optional[float] = None
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
        kwargs: dict = {"query": text_query, "knn": knn, "size": 10000}
        if min_score is not None:
            kwargs["min_score"] = min_score
        t0 = time()
        resp = await self._client.search(index=self.index, **kwargs)
        hits = [(hit["_id"], hit["_score"]) for hit in resp["hits"]["hits"]]
        logger.debug(
            "search %r → %d hits in %dms", query, len(hits), (time() - t0) * 1000
        )
        return hits
