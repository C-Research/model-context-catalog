from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel

from mcc.app import describe_tools, execute, search
from mcc.auth.models import UserModel
from mcc.loader import loader
from mcc.middleware import current_user_var
from fastmcp.server.elicitation import AcceptedElicitation, CancelledElicitation, DeclinedElicitation


def _ctx_raises():
    """Mock ctx whose elicit() raises — simulates a client that doesn't support elicitation."""
    ctx = MagicMock()
    ctx.elicit = AsyncMock(side_effect=Exception("elicitation not supported"))
    return ctx


def _ctx_accepts(**data):
    """Mock ctx whose elicit() returns an AcceptedElicitation with the given data fields."""
    class _Data(BaseModel):
        model_config = {"extra": "allow"}

    instance = _Data(**data)
    ctx = MagicMock()
    ctx.elicit = AsyncMock(return_value=AcceptedElicitation(data=instance))
    return ctx


def _ctx_declines():
    ctx = MagicMock()
    ctx.elicit = AsyncMock(return_value=DeclinedElicitation())
    return ctx


def _ctx_cancels():
    ctx = MagicMock()
    ctx.elicit = AsyncMock(return_value=CancelledElicitation())
    return ctx


class TestSearch:
    async def test_matches_by_name(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        await loader.save()
        result = await search("echo")
        assert "echo" in result
        assert "Echoes back" in result

    async def test_no_match(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        await loader.save()
        result = await search("zzz_nonexistent", min_score=999.0)
        assert result.startswith("No tools matched your query.")

    async def test_grouped_tool_inaccessible_anonymous(self, load_fixture):
        load_fixture("tools_grouped.yaml")
        await loader.save()
        result = await search("echo")
        assert result.startswith("No tools matched your query.")


class TestExecute:
    async def test_execute_public_tool(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        result = await execute(_ctx_raises(), "echo", {"message": "hi"})
        assert result == ["hi"]

    @pytest.mark.smoke
    async def test_execute_grouped_tool_unauthorized(self, load_fixture):
        load_fixture("tools_grouped.yaml")
        result = await execute(_ctx_raises(), "example.echo", {"message": "hi"})
        assert result.startswith("Unauthorized")

    @pytest.mark.smoke
    async def test_execute_unknown_tool(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        result = await execute(_ctx_raises(), "nonexistent", {})
        assert "Unknown tool" in result

    @pytest.mark.smoke
    async def test_execute_validation_error(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        result = await execute(_ctx_raises(), "echo", {})
        assert "Validation error" in result

    async def test_elicit_accepted_executes_tool(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        result = await execute(_ctx_accepts(message="elicited"), "echo", {})
        assert result == ["elicited"]

    async def test_elicit_declined_returns_cancelled(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        result = await execute(_ctx_declines(), "echo", {})
        assert result == "Execution cancelled: required parameters not provided"

    async def test_elicit_cancelled_returns_cancelled(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        result = await execute(_ctx_cancels(), "echo", {})
        assert result == "Execution cancelled: required parameters not provided"

    async def test_elicit_unsupported_client_falls_through(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        result = await execute(_ctx_raises(), "echo", {})
        assert "Validation error" in result

    async def test_elicit_not_triggered_when_params_provided(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        ctx = _ctx_accepts(message="should not be called")
        result = await execute(ctx, "echo", {"message": "direct"})
        ctx.elicit.assert_not_awaited()
        assert result == ["direct"]

    async def test_elicit_skipped_for_list_param(self, load_fixture):
        load_fixture("tools_list_param.yaml")
        ctx = _ctx_accepts()
        result = await execute(ctx, "join", {})
        ctx.elicit.assert_not_awaited()
        assert "Validation error" in result


class TestDescribeTools:
    async def test_lists_accessible_tools(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        result = await describe_tools()
        assert "## echo" in result
        assert "Echoes back" in result

    async def test_format(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        result = await describe_tools()
        assert result.startswith("## echo\n")

    async def test_grouped_tools_inaccessible_anonymous(self, load_fixture):
        load_fixture("tools_grouped.yaml")
        result = await describe_tools()
        assert result == "No tools available."

    async def test_groups_and_filter(self, load_fixture):
        load_fixture("tools_multigroup.yaml")
        current_user_var.set(UserModel(username="test", groups=["a", "b"]))
        try:
            result = await describe_tools(["a", "b"])
            assert "a.b.multi_ab" in result
            assert "a.single_a" not in result
            assert "b.single_b" not in result
        finally:
            current_user_var.set(None)

    async def test_groups_filter_no_match(self, load_fixture):
        load_fixture("tools_multigroup.yaml")
        current_user_var.set(UserModel(username="test", groups=["a", "b"]))
        try:
            result = await describe_tools(["a", "b", "nonexistent"])
            assert result == "No tools available."
        finally:
            current_user_var.set(None)

    async def test_empty_description(self, load_fixture):
        load_fixture("tools_no_description.yaml")
        result = await describe_tools()
        assert "## doc_tool" in result
