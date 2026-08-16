"""Backend-agnostic helpers shared by ``mcc.db.es`` and ``mcc.db.os``.

Nothing here talks to a search backend directly — just the embedding model
used by both `ToolIndex` implementations to vectorize a tool's signature.
"""

import asyncio
from time import time

from fastembed import TextEmbedding

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
