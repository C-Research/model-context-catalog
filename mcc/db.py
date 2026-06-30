import asyncio
from time import time
from typing import Optional
from urllib.parse import parse_qs, urlparse, urlunparse

from elasticsearch import AsyncElasticsearch
from fastembed import TextEmbedding

from mcc.esindex import ESIndex as _ESIndexBase
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


class ESIndex(_ESIndexBase):
    """mcc's ES index: connects to ``ELASTICSEARCH_URL`` and pings on enter.

    Document operations are inherited from the shared, settings-agnostic base;
    only the client construction is mcc-specific.
    """

    ping_on_enter = True

    def _make_client(self) -> AsyncElasticsearch:
        return AsyncElasticsearch(**_client_kwargs())


class UsersIndex(ESIndex):
    index = settings.USER_INDEX
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


class KeysIndex(ESIndex):
    index = settings.KEY_INDEX
    mapping = {
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


class ToolIndex(ESIndex):
    index = settings.TOOL_INDEX
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

    async def signatures(self) -> list[str]:
        """Return every indexed tool's signature, ordered by tool key.

        Reads straight from ES so callers get the catalog regardless of whether
        the in-memory loader is populated (it is not in an exec subprocess)."""
        resp = await self._client.search(
            index=self.index, query={"match_all": {}}, size=10000
        )
        hits = sorted(
            (hit["_id"], hit["_source"]["signature"])
            for hit in resp["hits"]["hits"]
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
