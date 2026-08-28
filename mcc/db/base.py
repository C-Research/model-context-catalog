"""Backend-agnostic helpers shared by ``mcc.db.es`` and ``mcc.db.os``.

Covers everything that doesn't depend on the Elasticsearch/OpenSearch client's
call conventions: the embedding model, index lifecycle (enter/exit), the
identical `UsersIndex`/`KeysIndex` mappings, connection-URL parsing, and the
hit-shaping/logging helpers ``ToolIndex.signatures``/``query`` share. The
per-document CRUD methods (`get`/`put`/`search`/...) stay in each backend
module since the two clients take incompatible kwargs for the same operation.
"""

import asyncio
from time import time
from typing import TYPE_CHECKING, ClassVar
from urllib.parse import parse_qs, urlparse, urlunparse

from fastembed import TextEmbedding

from mcc.models import ToolModel
from mcc.settings import logger, settings

_embedding_model: TextEmbedding | None = None


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


class IndexLifecycle:
    """Async context-manager scaffolding shared by both backends' index bases.

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

    def _make_client(self):
        """Return the client this index operates against.

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


USERS_MAPPING: dict = {
    "mappings": {
        "properties": {
            "username": {"type": "keyword"},
            "email": {"type": "keyword"},
            "groups": {"type": "keyword"},
            "tools": {"type": "keyword"},
        }
    }
}

KEYS_MAPPING: dict = {
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


def parse_backend_url(
    url: str,
) -> tuple[str, str, bool | None, tuple[str, str] | None]:
    """Parse an ES/OS connection URL into its shared, backend-neutral parts.

    Returns ``(scheme, bare_url, verify_certs, basic_auth)``: ``bare_url`` has
    userinfo and the query string stripped (both clients are unreliable about
    accepting them inline), ``verify_certs`` is the parsed `?verify_certs=`
    flag (``None`` if absent), and ``basic_auth`` is a ``(user, password)``
    tuple if the URL carried credentials.
    """
    parsed = urlparse(url)

    verify_certs = None
    params = parse_qs(parsed.query)
    if "verify_certs" in params:
        verify_certs = params["verify_certs"][0].lower() not in ("false", "0", "no")

    basic_auth = (parsed.username, parsed.password or "") if parsed.username else None

    netloc = parsed.hostname or ""
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    bare_url = urlunparse(parsed._replace(netloc=netloc, query=""))

    return parsed.scheme, bare_url, verify_certs, basic_auth


def sort_signatures(hits: list[dict]) -> list[str]:
    """Sort raw ES/OS hits by tool key (`_id`) and return their signatures."""
    ordered = sorted((hit["_id"], hit["_source"]["signature"]) for hit in hits)
    return [sig for _, sig in ordered]


def score_hits(hits: list[dict]) -> list[tuple[str, float]]:
    """Shape raw ES/OS hits into `(id, score)` pairs."""
    return [(hit["_id"], hit["_score"]) for hit in hits]


def log_query(query: str, hits: list[tuple[str, float]], t0: float) -> None:
    logger.debug(
        "search %r → %d hits in %dms", query, len(hits), (time() - t0) * 1000
    )


class ToolIndexMixin:
    """`ToolIndex` behavior shared once a backend implements `put`/`search`."""

    if TYPE_CHECKING:

        async def put(self, id: str, doc: dict, refresh: bool = True) -> None: ...

    async def index_tool(self, tool: ToolModel) -> None:
        await self.put(
            tool.key,
            {
                "signature": tool.signature,
                "groups": tool.groups,
                "embedding": await embed(tool.signature),
            },
        )
