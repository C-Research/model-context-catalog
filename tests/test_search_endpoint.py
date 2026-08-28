import json

from mcc.audit import SearchAuditIndex
from mcc.auth import create_user
from mcc.auth.keys import create_key
from mcc.loader import loader
from mcc.routes import search_tools
from mcc.settings import settings as real_settings
from starlette.requests import Request


def _request(headers=None, query=""):
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    return Request({"type": "http", "headers": raw, "query_string": query.encode()})


def _body(response) -> str:
    return response.body.decode()


def _json(response):
    return json.loads(_body(response))


class TestSearchEndpointAccess:
    async def test_anonymous_returns_public_tools_only(self, load_fixture):
        load_fixture("tools_ungrouped.yaml", "tools_grouped.yaml")
        await loader.save()
        response = await search_tools(_request(query="q=echo"))
        keys = {t["key"] for t in _json(response)}
        assert keys == {"echo"}
        assert "example.echo" not in keys

    async def test_authenticated_widens_to_granted_tools(
        self, users_idx, keys_idx, load_fixture
    ):
        load_fixture("tools_ungrouped.yaml", "tools_grouped.yaml")
        await loader.save()
        await create_user("ci-bot", tools=["example.echo"])
        raw = await create_key("ci-bot", ttl_days=90)

        response = await search_tools(
            _request({"Authorization": f"Bearer {raw}"}, query="q=echo")
        )
        keys = {t["key"] for t in _json(response)}
        assert keys == {"echo", "example.echo"}

    async def test_invalid_key_falls_back_to_public_only(self, load_fixture):
        load_fixture("tools_ungrouped.yaml", "tools_grouped.yaml")
        await loader.save()
        response = await search_tools(
            _request({"Authorization": "Bearer garbage"}, query="q=echo")
        )
        keys = {t["key"] for t in _json(response)}
        assert keys == {"echo"}


class TestSearchEndpointResults:
    async def test_response_includes_score_and_tool_fields(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        await loader.save()
        response = await search_tools(_request(query="q=echo"))
        assert response.media_type == "application/json"
        [result] = _json(response)
        assert set(result.keys()) == {
            "score",
            "key",
            "groups",
            "params",
            "return_type",
            "description",
            "example",
        }
        assert result["key"] == "echo"
        assert isinstance(result["score"], float)

    async def test_no_match_returns_empty_list(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        await loader.save()
        response = await search_tools(
            _request(query="q=zzz_nonexistent&min_score=999")
        )
        assert _json(response) == []

    async def test_min_score_filters_low_scoring_results(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        await loader.save()
        response = await search_tools(_request(query="q=echo&min_score=999"))
        assert _json(response) == []

    async def test_invalid_min_score_returns_400(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        await loader.save()
        response = await search_tools(_request(query="q=echo&min_score=notanumber"))
        assert response.status_code == 400
        assert "min_score" in _json(response)["error"]


class TestSearchEndpointAudit:
    async def test_records_ordered_keys_and_scores(self, load_fixture, search_audit_idx):
        load_fixture("tools_ungrouped.yaml")
        await loader.save()
        await search_tools(_request(query="q=echo"))
        docs = await search_audit_idx.search({"match_all": {}})
        assert len(docs) == 1
        doc = docs[0]
        assert doc["query"] == "echo"
        assert doc["username"] == "anonymous"
        assert "echo=" in doc["results"]

    async def test_no_record_when_disabled(self, load_fixture, monkeypatch):
        monkeypatch.setattr(SearchAuditIndex, "index", "mcc-search-audit-test")
        assert not real_settings.AUDIT_SEARCH_INDEX  # disabled for the whole test session
        load_fixture("tools_ungrouped.yaml")
        await loader.save()
        await search_tools(_request(query="q=echo"))
        async with SearchAuditIndex() as idx:
            await idx.create()
            docs = await idx.search({"match_all": {}})
        assert docs == []

    async def test_only_accessible_results_recorded(self, load_fixture, search_audit_idx):
        load_fixture("tools_ungrouped.yaml", "tools_grouped.yaml")
        await loader.save()
        await search_tools(_request(query="q=echo"))
        docs = await search_audit_idx.search({"match_all": {}})
        assert len(docs) == 1
        results = docs[0]["results"]
        assert "echo=" in results
        assert "example.echo" not in results
