"""Unit-level coverage for the OpenSearch backend's `bulk_put`, kept symmetric
with the Elasticsearch backend's bulk write path. Runs against a fake client
(no live OpenSearch cluster needed) since the test suite has no OpenSearch
integration fixture — `opensearch-py` is an optional extra, so these tests
skip entirely when it isn't installed rather than failing a default test run.
"""

from unittest.mock import AsyncMock

import pytest

pytest.importorskip("opensearchpy")

from mcc.db.os import _OSIndexBase  # noqa: E402


class _FakeIndicesClient:
    def __init__(self):
        self.refresh = AsyncMock()


class _FakeClient:
    def __init__(self):
        self.indices = _FakeIndicesClient()


class _FakeToolIndex(_OSIndexBase):
    index = "fake-tools-index"


class TestOSBulkPut:
    async def test_bulk_put_calls_async_bulk_once(self, monkeypatch):
        idx = _FakeToolIndex()
        idx._client = _FakeClient()
        calls = []

        async def fake_async_bulk(client, actions):
            calls.append((client, actions))
            return (len(actions), [])

        monkeypatch.setattr("mcc.db.os.async_bulk", fake_async_bulk)

        actions = [
            {
                "_index": "fake-tools-index",
                "_id": "a",
                "_source": {"signature": "a()", "groups": [], "embedding": [0.1]},
            },
            {
                "_index": "fake-tools-index",
                "_id": "b",
                "_source": {"signature": "b()", "groups": [], "embedding": [0.2]},
            },
        ]
        await idx.bulk_put(actions)

        assert calls == [(idx._client, actions)]

    async def test_bulk_put_refreshes_exactly_once(self, monkeypatch):
        idx = _FakeToolIndex()
        idx._client = _FakeClient()

        async def fake_async_bulk(client, actions):
            return (len(actions), [])

        monkeypatch.setattr("mcc.db.os.async_bulk", fake_async_bulk)

        await idx.bulk_put([{"_index": "fake-tools-index", "_id": "a", "_source": {}}])

        idx._client.indices.refresh.assert_awaited_once_with(index="fake-tools-index")
