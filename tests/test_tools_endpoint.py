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


def _tools(response) -> list[dict]:
    return _json(response)["tools"]


class TestToolsEndpointAccess:
    async def test_anonymous_returns_public_tools_only(self, load_fixture):
        load_fixture("tools_ungrouped.yaml", "tools_grouped.yaml")
        response = await tools(_request())
        keys = {t["key"] for t in _tools(response)}
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
        keys = {t["key"] for t in _tools(response)}
        assert keys == {"echo", "example.echo"}

    async def test_invalid_key_falls_back_to_public_only(self, load_fixture):
        load_fixture("tools_ungrouped.yaml", "tools_grouped.yaml")
        response = await tools(_request({"Authorization": "Bearer garbage"}))
        keys = {t["key"] for t in _tools(response)}
        assert keys == {"echo"}


class TestToolsEndpointJson:
    async def test_default_format_is_json_with_documented_fields(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        response = await tools(_request())
        assert response.media_type == "application/json"
        [tool] = _tools(response)
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
        [tool] = _tools(response)
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
        [tool] = _tools(response)
        assert tool["return_type"] == "str | (int, str, str)"

    async def test_unrecognized_format_falls_back_to_json(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        default = await tools(_request())
        unknown = await tools(_request(query="format=xml"))
        assert unknown.media_type == "application/json"
        assert _json(default) == _json(unknown)


class TestToolsEndpointGroupsFilter:
    async def test_no_groups_param_returns_all_accessible(
        self, users_idx, keys_idx, load_fixture
    ):
        from mcc.auth import create_user
        from mcc.auth.keys import create_key

        load_fixture("tools_ungrouped.yaml", "tools_grouped.yaml")
        await create_user("ci-bot", tools=["example.echo"])
        raw = await create_key("ci-bot", ttl_days=90)

        response = await tools(_request({"Authorization": f"Bearer {raw}"}))
        keys = {t["key"] for t in _tools(response)}
        assert keys == {"echo", "example.echo"}

    async def test_groups_filter_restricts_to_matching_tools(
        self, users_idx, keys_idx, load_fixture
    ):
        from mcc.auth import create_user
        from mcc.auth.keys import create_key

        load_fixture("tools_ungrouped.yaml", "tools_grouped.yaml")
        await create_user("ci-bot", tools=["example.echo"])
        raw = await create_key("ci-bot", ttl_days=90)

        response = await tools(
            _request({"Authorization": f"Bearer {raw}"}, query="groups=example")
        )
        keys = {t["key"] for t in _tools(response)}
        assert keys == {"example.echo"}

    async def test_groups_filter_with_no_match_returns_empty(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        response = await tools(_request(query="groups=nonexistent"))
        assert _tools(response) == []

    async def test_comma_separated_groups_are_combined(
        self, users_idx, keys_idx, load_fixture
    ):
        from mcc.auth import create_user
        from mcc.auth.keys import create_key

        load_fixture("tools_ungrouped.yaml", "tools_grouped.yaml")
        await create_user("ci-bot", tools=["example.echo"])
        raw = await create_key("ci-bot", ttl_days=90)

        response = await tools(
            _request(
                {"Authorization": f"Bearer {raw}"},
                query="groups=nonexistent,example",
            )
        )
        keys = {t["key"] for t in _tools(response)}
        assert keys == {"example.echo"}

    async def test_repeated_groups_params_are_combined(
        self, users_idx, keys_idx, load_fixture
    ):
        from mcc.auth import create_user
        from mcc.auth.keys import create_key

        load_fixture("tools_ungrouped.yaml", "tools_grouped.yaml")
        await create_user("ci-bot", tools=["example.echo"])
        raw = await create_key("ci-bot", ttl_days=90)

        response = await tools(
            _request(
                {"Authorization": f"Bearer {raw}"},
                query="groups=nonexistent&groups=example",
            )
        )
        keys = {t["key"] for t in _tools(response)}
        assert keys == {"example.echo"}


class TestToolsEndpointPagination:
    async def test_defaults_to_first_ten_with_no_more(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        response = await tools(_request())
        body = _json(response)
        assert len(body["tools"]) == 1
        assert body["has_more"] is False
        assert body["next_offset"] is None

    async def test_limit_below_total_sets_has_more_and_next_offset(
        self, users_idx, keys_idx, load_fixture
    ):
        from mcc.auth import create_user
        from mcc.auth.keys import create_key

        load_fixture("tools_ungrouped.yaml", "tools_grouped.yaml")
        await create_user("ci-bot", tools=["example.echo"])
        raw = await create_key("ci-bot", ttl_days=90)

        response = await tools(
            _request({"Authorization": f"Bearer {raw}"}, query="limit=1")
        )
        body = _json(response)
        assert len(body["tools"]) == 1
        assert body["has_more"] is True
        assert body["next_offset"] == 1

    async def test_offset_advances_page(self, users_idx, keys_idx, load_fixture):
        from mcc.auth import create_user
        from mcc.auth.keys import create_key

        load_fixture("tools_ungrouped.yaml", "tools_grouped.yaml")
        await create_user("ci-bot", tools=["example.echo"])
        raw = await create_key("ci-bot", ttl_days=90)
        headers = {"Authorization": f"Bearer {raw}"}

        first = _json(await tools(_request(headers, query="limit=1")))
        second = _json(
            await tools(
                _request(headers, query=f"limit=1&offset={first['next_offset']}")
            )
        )
        assert first["tools"][0]["key"] != second["tools"][0]["key"]
        assert second["has_more"] is False
        assert second["next_offset"] is None

    async def test_negative_offset_is_rejected(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        response = await tools(_request(query="offset=-1"))
        assert response.status_code == 400

    async def test_non_integer_limit_is_rejected(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        response = await tools(_request(query="limit=abc"))
        assert response.status_code == 400

    async def test_limit_at_max_is_allowed(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        response = await tools(_request(query="limit=50"))
        assert response.status_code == 200

    async def test_limit_over_max_is_rejected(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        response = await tools(_request(query="limit=51"))
        assert response.status_code == 400


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
