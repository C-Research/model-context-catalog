import json

import mcc.routes as routes_module
import pytest
from mcc.auth import create_user
from mcc.auth.keys import create_key
from mcc.context import current_user_var
from mcc.middleware import check_rate_limit, record_tool_call
from mcc.routes import healthz, metrics, route, tool_detail, tool_execute, tools, users_list, whoami
from mcc.settings import settings as real_settings
from starlette.requests import Request


def _request(headers=None, query="", path_params=None, body=b""):
    raw_headers = [
        (k.lower().encode(), v.encode()) for k, v in (headers or {}).items()
    ]
    request = Request(
        {
            "type": "http",
            "headers": raw_headers,
            "query_string": query.encode(),
            "path_params": path_params or {},
        }
    )
    request._body = body
    return request


class TestRouteModes:
    """@route's four auth modes and its contradiction guard, exercised through
    the already-registered production handlers rather than registering
    throwaway test routes (since @route self-registers onto the shared `mcp`
    instance as a side effect of decoration)."""

    async def test_default_mode_missing_key_returns_401(self):
        response = await whoami(_request())
        assert response.status_code == 401

    async def test_default_mode_valid_key_resolves_user(self, users_idx, keys_idx):
        await create_user("ci-bot")
        raw = await create_key("ci-bot", ttl_days=90)
        response = await whoami(_request({"Authorization": f"Bearer {raw}"}))
        assert response.status_code == 200
        assert json.loads(response.body)["username"] == "ci-bot"

    async def test_anonymous_mode_ignores_a_present_valid_key(self, users_idx, keys_idx):
        await create_user("ci-bot", groups=["admin"])
        raw = await create_key("ci-bot", ttl_days=90)
        # healthz's body never reads request.user; this confirms anonymous
        # mode doesn't 401 or otherwise choke when a valid key is present.
        response = await healthz(_request({"Authorization": f"Bearer {raw}"}))
        assert response.status_code == 200

    async def test_optional_mode_no_key_does_not_401(self):
        response = await tools(_request())
        assert response.status_code == 200

    async def test_optional_mode_valid_key_resolves_user(self, users_idx, keys_idx):
        await create_user("ci-bot")
        raw = await create_key("ci-bot", ttl_days=90)
        response = await tools(_request({"Authorization": f"Bearer {raw}"}))
        assert response.status_code == 200

    async def test_admin_mode_missing_key_returns_401(self):
        response = await users_list(_request())
        assert response.status_code == 401

    async def test_admin_mode_non_admin_key_returns_401(self, users_idx, keys_idx):
        await create_user("ci-bot", groups=["public"])
        raw = await create_key("ci-bot", ttl_days=90)
        response = await users_list(_request({"Authorization": f"Bearer {raw}"}))
        assert response.status_code == 401

    async def test_admin_mode_admin_key_returns_200(self, users_idx, keys_idx):
        await create_user("ci-bot", groups=["admin"])
        raw = await create_key("ci-bot", ttl_days=90)
        response = await users_list(_request({"Authorization": f"Bearer {raw}"}))
        assert response.status_code == 200

    def test_admin_with_anonymous_raises_at_decoration_time(self):
        with pytest.raises(ValueError):
            route("/__test_invalid__", admin=True, anonymous=True)

    def test_admin_with_optional_raises_at_decoration_time(self):
        with pytest.raises(ValueError):
            route("/__test_invalid__", admin=True, optional=True)


class TestCurrentUserVarSetByRoute:
    """route()'s wrapper mirrors AuthMiddleware's job for the MCP transport:
    sets current_user_var, not just request.scope["user"], so identity is
    uniformly readable from ToolModel.call()'s hook regardless of transport."""

    async def test_resolved_user_sets_current_user_var(self, users_idx, keys_idx):
        await create_user("ci-bot")
        raw = await create_key("ci-bot", ttl_days=90)
        try:
            await whoami(_request({"Authorization": f"Bearer {raw}"}))
            assert current_user_var.get().username == "ci-bot"
        finally:
            current_user_var.set(None)

    async def test_anonymous_route_sets_current_user_var_to_none(self):
        from mcc.auth.models import UserModel

        current_user_var.set(UserModel(username="stale"))
        try:
            await healthz(_request())
            assert current_user_var.get() is None
        finally:
            current_user_var.set(None)


class TestApiKeyQueryParamFallback:
    async def test_query_param_used_when_no_header_present(self, users_idx, keys_idx):
        await create_user("ci-bot")
        raw = await create_key("ci-bot", ttl_days=90)
        response = await whoami(_request(query=f"api-key={raw}"))
        assert response.status_code == 200
        assert json.loads(response.body)["username"] == "ci-bot"

    async def test_header_takes_precedence_over_query_param(self, users_idx, keys_idx):
        await create_user("ci-bot")
        raw = await create_key("ci-bot", ttl_days=90)
        response = await whoami(
            _request({"X-API-Key": raw}, query="api-key=garbage")
        )
        assert response.status_code == 200
        assert json.loads(response.body)["username"] == "ci-bot"


class TestToolDetail:
    async def test_unknown_key_returns_404(self, load_fixture):
        load_fixture("tools_public.yaml")
        response = await tool_detail(_request(path_params={"key": "no.such.tool"}))
        assert response.status_code == 404

    async def test_inaccessible_key_returns_404_same_as_unknown(self, load_fixture):
        load_fixture("tools_grouped.yaml")
        response = await tool_detail(_request(path_params={"key": "example.echo"}))
        assert response.status_code == 404

    async def test_accessible_public_tool_returns_detail(self, load_fixture):
        load_fixture("tools_public.yaml")
        response = await tool_detail(_request(path_params={"key": "public.echo"}))
        assert response.status_code == 200
        assert json.loads(response.body)["key"] == "public.echo"


class TestToolExecute:
    async def test_unknown_key_returns_404_plain_text(self, load_fixture):
        load_fixture("tools_public.yaml")
        response = await tool_execute(
            _request(path_params={"key": "no.such.tool"})
        )
        assert response.status_code == 404
        assert bytes(response.body).decode() == "Not found"

    async def test_inaccessible_key_returns_404_same_as_unknown(self, load_fixture):
        load_fixture("tools_grouped.yaml")
        response = await tool_execute(_request(path_params={"key": "example.echo"}))
        assert response.status_code == 404

    async def test_successful_call_returns_result_as_text(self, load_fixture):
        load_fixture("tools_public.yaml")
        response = await tool_execute(
            _request(
                path_params={"key": "public.echo"},
                body=json.dumps({"message": "hi"}).encode(),
            )
        )
        assert response.status_code == 200
        assert json.loads(bytes(response.body).decode()) == ["hi"]

    async def test_non_object_body_returns_400(self, load_fixture):
        load_fixture("tools_public.yaml")
        response = await tool_execute(
            _request(path_params={"key": "public.echo"}, body=b"[1, 2, 3]")
        )
        assert response.status_code == 400

    async def test_malformed_json_body_returns_400(self, load_fixture):
        load_fixture("tools_public.yaml")
        response = await tool_execute(
            _request(path_params={"key": "public.echo"}, body=b"{not json")
        )
        assert response.status_code == 400

    async def test_validation_error_returns_400_one_line_by_default(self, load_fixture):
        load_fixture("tools_public.yaml")
        response = await tool_execute(
            _request(path_params={"key": "public.echo"}, body=b"{}")
        )
        assert response.status_code == 400
        text = bytes(response.body).decode()
        assert "ValidationError" in text
        assert "Traceback (most recent call last):" not in text

    async def test_validation_error_returns_full_traceback_when_debug(
        self, load_fixture, monkeypatch
    ):
        load_fixture("tools_public.yaml")
        monkeypatch.setattr(routes_module.settings, "DEBUG", True)
        response = await tool_execute(
            _request(path_params={"key": "public.echo"}, body=b"{}")
        )
        assert response.status_code == 400
        assert "Traceback (most recent call last):" in bytes(response.body).decode()


class TestToolExecuteRateLimit:
    async def test_shares_bucket_with_mcp_execute(self, load_fixture, monkeypatch):
        load_fixture("tools_public.yaml")
        monkeypatch.setattr(real_settings.rate_limit, "enabled", True)
        monkeypatch.setattr(real_settings.rate_limit, "default", "1/60s")

        first = await tool_execute(
            _request(
                path_params={"key": "public.echo"},
                body=json.dumps({"message": "hi"}).encode(),
            )
        )
        assert first.status_code == 200

        # Same bucket key format RateLimitMiddleware uses for MCP execute() —
        # already exhausted by the REST call above.
        exceeded, _remaining = await check_rate_limit("public.echo", "anon")
        assert exceeded is True

    async def test_throttled_call_returns_429(self, load_fixture, monkeypatch):
        load_fixture("tools_public.yaml")
        monkeypatch.setattr(real_settings.rate_limit, "enabled", True)
        monkeypatch.setattr(real_settings.rate_limit, "default", "1/60s")
        body = json.dumps({"message": "hi"}).encode()

        first = await tool_execute(
            _request(path_params={"key": "public.echo"}, body=body)
        )
        second = await tool_execute(
            _request(path_params={"key": "public.echo"}, body=body)
        )
        assert first.status_code == 200
        assert second.status_code == 429


class TestUsersList:
    async def test_keys_omitted_by_default(self, users_idx, keys_idx):
        await create_user("ci-bot", groups=["admin"])
        raw = await create_key("ci-bot", ttl_days=90)
        response = await users_list(_request({"Authorization": f"Bearer {raw}"}))
        body = json.loads(response.body)
        assert all("key" not in u for u in body)

    async def test_keys_included_when_requested(self, users_idx, keys_idx):
        await create_user("ci-bot", groups=["admin"])
        raw = await create_key("ci-bot", ttl_days=90)
        response = await users_list(
            _request({"Authorization": f"Bearer {raw}"}, query="keys=true")
        )
        body = json.loads(response.body)
        ci_bot = next(u for u in body if u["username"] == "ci-bot")
        assert ci_bot["key"]["prefix"].startswith("mcc_")


class TestMetrics:
    async def test_anonymous_access_returns_200(self):
        response = await metrics(_request())
        assert response.status_code == 200

    async def test_reflects_calls_from_either_transport(self):
        record_tool_call("public.echo", "success", 0.01)
        response = await metrics(_request())
        text = bytes(response.body).decode()
        assert 'mcc_tool_calls_total{status="success",tool="public.echo"}' in text
