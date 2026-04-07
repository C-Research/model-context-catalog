from pathlib import Path
from unittest.mock import patch

import pytest

from mcc.app import (
    catalog_tool_by_key,
    catalog_tools,
    debug_error,
    explain_tool,
    find_and_run,
    user_me,
)
from mcc.auth.models import UserModel
from mcc.loader import loader
from mcc.middleware import AuthMiddleware, LoggingMiddleware, current_user_var

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _clean_loader():
    loader.clear()
    yield
    loader.clear()


def _load(filename: str):
    loader.load(FIXTURES / filename)


# --- Middleware ---


@pytest.mark.smoke
class TestAuthMiddleware:
    async def test_resolves_authenticated_user(self):
        user = UserModel(username="alice", email="a@b.com", groups=["admin"])
        with patch("mcc.middleware.get_current_user", return_value=user):
            middleware = AuthMiddleware()

            async def _noop(ctx):
                return None

            await middleware.on_message(None, _noop)
            assert current_user_var.get() == user

    async def test_anonymous_sets_none(self):
        with patch("mcc.middleware.get_current_user", return_value=None):
            middleware = AuthMiddleware()

            async def _noop(ctx):
                return None

            await middleware.on_message(None, _noop)
            assert current_user_var.get() is None


@pytest.mark.smoke
class TestLoggingMiddleware:
    async def test_logs_tool_call(self, caplog):
        import logging

        current_user_var.set(None)

        class FakeMessage:
            name = "test.tool"
            arguments = {"key": "val"}

        class FakeContext:
            message = FakeMessage()

        middleware = LoggingMiddleware()

        async def _noop(ctx):
            return "result"

        mcc_logger = logging.getLogger("mcc")
        mcc_logger.propagate = True
        try:
            with caplog.at_level("INFO", logger="mcc"):
                await middleware.on_call_tool(FakeContext(), _noop)

            assert "anonymous calling test.tool" in caplog.text
            assert "completed test.tool" in caplog.text
        finally:
            mcc_logger.propagate = False


# --- Resources ---


@pytest.mark.smoke
class TestCatalogResource:
    async def test_returns_accessible_tools(self):
        _load("tools_ungrouped.yaml")
        current_user_var.set(None)
        result = await catalog_tools()
        assert "echo" in result

    async def test_filters_grouped_tools_for_anonymous(self):
        _load("tools_grouped.yaml")
        current_user_var.set(None)
        result = await catalog_tools()
        assert result == "No accessible tools."

    async def test_admin_sees_grouped_tools(self):
        _load("tools_grouped.yaml")
        current_user_var.set(UserModel(username="admin", groups=["admin"]))
        result = await catalog_tools()
        assert "echo" in result


@pytest.mark.smoke
class TestToolResourceTemplate:
    async def test_accessible_tool(self):
        _load("tools_ungrouped.yaml")
        current_user_var.set(None)
        result = await catalog_tool_by_key("echo")
        assert "echo" in result

    async def test_inaccessible_tool(self):
        _load("tools_grouped.yaml")
        current_user_var.set(None)
        result = await catalog_tool_by_key("example.echo")
        assert "not found" in result

    async def test_unknown_tool(self):
        result = await catalog_tool_by_key("nonexistent")
        assert "not found" in result


@pytest.mark.smoke
class TestUserResource:
    async def test_authenticated(self):
        current_user_var.set(
            UserModel(username="alice", email="a@b.com", groups=["ops"], tools=["echo"])
        )
        result = await user_me()
        assert result["username"] == "alice"
        assert result["email"] == "a@b.com"
        assert "ops" in result["groups"]
        assert "echo" in result["tools"]

    async def test_anonymous(self):
        current_user_var.set(None)
        result = await user_me()
        assert result["username"] == "anonymous"
        assert result["groups"] == []


# --- Prompts ---


@pytest.mark.smoke
class TestPrompts:
    def test_find_and_run(self):
        result = find_and_run("deploy the app")
        assert "deploy the app" in result
        assert "Search" in result or "search" in result.lower()

    def test_explain_tool(self):
        result = explain_tool("admin.shell")
        assert "admin.shell" in result
        assert "parameters" in result.lower()

    def test_debug_error(self):
        result = debug_error("admin.shell", "permission denied")
        assert "admin.shell" in result
        assert "permission denied" in result
        assert "fix" in result.lower() or "troubleshoot" in result.lower()
