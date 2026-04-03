from pathlib import Path

import pytest

from mcc.app import execute, search
from mcc.loader import loader

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _clean_loader():
    loader.clear()
    yield
    loader.clear()


def _load(filename: str):
    loader.load(FIXTURES / filename)


class TestSearch:
    @pytest.mark.asyncio
    async def test_matches_by_name(self):
        _load("tools_public.yaml")
        result = await search("echo")
        assert "echo" in result
        assert "Echoes back" in result

    @pytest.mark.asyncio
    async def test_no_match(self):
        _load("tools_public.yaml")
        assert await search("zzz_nonexistent") == "No tools matched your query."

    @pytest.mark.asyncio
    async def test_empty_query_returns_all(self):
        _load("tools_public.yaml")
        result = await search("")
        assert "echo" in result

    @pytest.mark.asyncio
    async def test_group_filter(self):
        _load("tools_public.yaml")
        assert "echo" in await search("", group="public")
        assert await search("", group="other") == "No tools matched your query."

    @pytest.mark.asyncio
    async def test_grouped_display_name(self):
        _load("tools_grouped.yaml")
        result = await search("echo", ctx=None)
        assert await search("echo") == "No tools matched your query."

    @pytest.mark.asyncio
    async def test_ungrouped_display_name(self):
        _load("tools_public.yaml")
        result = await search("echo")
        assert "public.echo" in result
        assert 'execute("public.echo"' in result


class TestExecute:
    @pytest.mark.asyncio
    async def test_execute_public_tool(self):
        _load("tools_public.yaml")
        result = await execute("public.echo", {"message": "hi"})
        assert result == ["hi"]

    @pytest.mark.asyncio
    async def test_execute_grouped_tool_unauthorized(self):
        _load("tools_grouped.yaml")
        result = await execute("example.echo", {"message": "hi"})
        assert result == "Unauthorized"

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self):
        _load("tools_public.yaml")
        result = await execute("nonexistent", {})
        assert "Unknown tool" in result

    @pytest.mark.asyncio
    async def test_execute_validation_error(self):
        _load("tools_public.yaml")
        result = await execute("public.echo", {})
        assert "Validation error" in result
