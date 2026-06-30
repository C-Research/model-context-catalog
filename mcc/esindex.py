"""Settings-agnostic async Elasticsearch index base class.

This module deliberately imports nothing from ``mcc.settings``, ``fastembed``,
or the tool model, so it can be reused by other services  without
pulling in mcc's configuration side-effects or heavy optional dependencies.

Subclasses declare an ``index`` name and ``mapping`` and implement
``_make_client`` to supply the Elasticsearch client the index operates against.
The index is an async context manager that owns that client for the block.
"""

from typing import Optional

from elasticsearch import AsyncElasticsearch


class ESIndex:
    """Async Elasticsearch index with scoped document operations.

    Used as an async context manager::

        async with SomeIndex() as idx:
            await idx.put("id", {...})

    Subclasses MUST set ``index`` / ``mapping`` and implement ``_make_client``.
    Set ``ping_on_enter = True`` to verify connectivity (``client.info()``) on
    enter — fail-fast at the cost of a round-trip.
    """

    index = "index"
    mapping: dict = {}
    ping_on_enter: bool = False

    def _make_client(self) -> AsyncElasticsearch:
        """Return the ES client this index operates against.

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

    async def get(self, id: str) -> Optional[dict]:
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
