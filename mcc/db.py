from elasticsearch import AsyncElasticsearch

from mcc.auth.models import UserModel
from mcc.models import ToolModel
from mcc.settings import settings


class ESIndex:
    """Async Elasticsearch index with scoped operations."""

    index = "index"
    mapping = {}

    async def __aenter__(self):
        cfg = settings.ELASTICSEARCH
        scheme = cfg.get("SCHEME", "http")
        host = cfg.get("HOST", "localhost")
        port = cfg.get("PORT", 9200)
        username = cfg.get("USERNAME", "")
        password = cfg.get("PASSWORD", "")
        api_key = cfg.get("API_KEY", "")
        kwargs: dict = {"hosts": [f"{scheme}://{host}:{port}"]}
        if api_key:
            kwargs["api_key"] = api_key
        elif username:
            kwargs["basic_auth"] = (username, password)
        self._client = AsyncElasticsearch(**kwargs)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._client.close()

    async def get(self, id: str) -> dict | None:
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
        """Run a query and return a list of _source dicts."""
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
            index=self.index, ignore_unavailable=ignore_unavailable
        )


class UsersIndex(ESIndex):
    index = settings.ELASTICSEARCH.USER_INDEX
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
    index = settings.ELASTICSEARCH.TOOL_INDEX
    mapping = {
        "mappings": {
            "properties": {
                "name": {"type": "text"},
                "description": {"type": "text"},
                "groups": {"type": "keyword"},
            }
        }
    }

    async def put(self, tool: ToolModel) -> None:
        await super().put(
            tool.key,
            {"name": tool.name, "description": tool.description, "groups": tool.groups},
        )

    async def search(self, query: str, group: str | None = None) -> list[str]:
        es_query: dict = {
            "multi_match": {
                "query": query,
                "fields": ["name^2", "description"],
                "fuzziness": "AUTO",
            }
        }
        if group is not None:
            es_query = {
                "bool": {
                    "must": es_query,
                    "filter": {"term": {"groups": group}},
                }
            }
        resp = await self._client.search(
            index=self.index, body={"query": es_query, "size": 10000}
        )
        return [hit["_id"] for hit in resp["hits"]["hits"]]
