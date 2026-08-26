import json

from mcc.loader import loader
from mcc.routes import tools
from starlette.requests import Request


def _request(headers=None, query=""):
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    return Request({"type": "http", "headers": raw, "query_string": query.encode()})


def _body(response) -> str:
    return response.body.decode()


def _json(response):
    return json.loads(_body(response))


class TestToolsEndpointAccess:
    async def test_anonymous_returns_public_tools_only(self, load_fixture):
        load_fixture("tools_ungrouped.yaml", "tools_grouped.yaml")
        response = await tools(_request())
        keys = {t["key"] for t in _json(response)}
        assert keys == {"echo"}
        assert "example.echo" not in keys

    async def test_authenticated_widens_to_granted_tools(
        self, users_idx, keys_idx, load_fixture
    ):
        from mcc.auth import create_user
        from mcc.auth.keys import create_key

        load_fixture("tools_ungrouped.yaml", "tools_grouped.yaml")
        await create_user("ci-bot", tools=["example.echo"])
        raw = await create_key("ci-bot", ttl_days=90)

        response = await tools(_request({"Authorization": f"Bearer {raw}"}))
        keys = {t["key"] for t in _json(response)}
        assert keys == {"echo", "example.echo"}

    async def test_invalid_key_falls_back_to_public_only(self, load_fixture):
        load_fixture("tools_ungrouped.yaml", "tools_grouped.yaml")
        response = await tools(_request({"Authorization": "Bearer garbage"}))
        keys = {t["key"] for t in _json(response)}
        assert keys == {"echo"}


class TestToolsEndpointJson:
    async def test_default_format_is_json_with_documented_fields(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        response = await tools(_request())
        assert response.media_type == "application/json"
        [tool] = _json(response)
        assert set(tool.keys()) == {
            "key",
            "groups",
            "params",
            "return_type",
            "description",
            "example",
        }
        [param] = tool["params"]
        assert set(param.keys()) == {
            "name",
            "type",
            "required",
            "default",
            "description",
            "example",
        }

    async def test_explicit_json_format_matches_default(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        default = await tools(_request())
        explicit = await tools(_request(query="format=json"))
        assert _json(default) == _json(explicit)

    async def test_internal_execution_fields_never_leak(self, load_fixture):
        load_fixture("tools_exec_timeout.yaml")
        response = await tools(_request())
        body = _body(response)
        assert "sleep 10" not in body
        [tool] = _json(response)
        for forbidden in (
            "fn",
            "exec",
            "curl",
            "python",
            "cwd",
            "env",
            "env_file",
            "env_passthrough",
            "limits",
            "transform",
        ):
            assert forbidden not in tool

    async def test_exec_tool_return_type_is_special_cased(self, load_fixture):
        load_fixture("tools_exec_timeout.yaml")
        response = await tools(_request())
        [tool] = _json(response)
        assert tool["return_type"] == "str | (int, str, str)"

    async def test_unrecognized_format_falls_back_to_json(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        default = await tools(_request())
        unknown = await tools(_request(query="format=xml"))
        assert unknown.media_type == "application/json"
        assert _json(default) == _json(unknown)


class TestToolsEndpointMarkdownAndHtml:
    async def test_md_format_returns_plain_text_signature_blocks(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        response = await tools(_request(query="format=md"))
        assert response.media_type == "text/plain"
        assert "## echo" in _body(response)

    async def test_html_format_renders_markdown_to_html(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        response = await tools(_request(query="format=html"))
        assert response.media_type == "text/html"
        assert "<h2>" in _body(response)

    async def test_html_is_rendered_form_of_md(self, load_fixture):
        loader.clear()
        load_fixture("tools_ungrouped.yaml")
        md = await tools(_request(query="format=md"))
        html = await tools(_request(query="format=html"))
        assert "## echo" in _body(md)
        assert "## echo" not in _body(html)
        assert "<h2>" in _body(html)
