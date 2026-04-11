import pytest

from mcc.app import describe_tools, execute, search
from mcc.auth.models import UserModel
from mcc.loader import loader
from mcc.middleware import current_user_var


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
        result = await execute("echo", {"message": "hi"})
        assert result == ["hi"]

    @pytest.mark.smoke
    async def test_execute_grouped_tool_unauthorized(self, load_fixture):
        load_fixture("tools_grouped.yaml")
        result = await execute("example.echo", {"message": "hi"})
        assert result.startswith("Unauthorized")

    @pytest.mark.smoke
    async def test_execute_unknown_tool(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        result = await execute("nonexistent", {})
        assert "Unknown tool" in result

    @pytest.mark.smoke
    async def test_execute_validation_error(self, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        result = await execute("echo", {})
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
