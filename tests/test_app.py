from pathlib import Path

import pytest
import pytest_asyncio

from mcc.app import execute, search
from mcc.loader import loader
from mcc.db import ToolIndex

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _clean_loader():
    loader.clear()
    yield
    loader.clear()


@pytest_asyncio.fixture(autouse=True)
async def _fresh_tool_index():
    async with ToolIndex() as idx:
        await idx.drop()
        await idx.create()
    yield
    async with ToolIndex() as idx:
        await idx.drop()


def _load(filename: str):
    loader.load(FIXTURES / filename)


class TestSearch:
    @pytest.mark.asyncio
    async def test_matches_by_name(self):
        _load("tools_public.yaml")
        await loader.save()
        result = await search("echo")
        assert "echo" in result
        assert "Echoes back" in result

    @pytest.mark.asyncio
    async def test_no_match(self):
        _load("tools_public.yaml")
        await loader.save()
        assert await search("zzz_nonexistent") == "No tools matched your query."

    @pytest.mark.asyncio
    async def test_group_filter(self):
        _load("tools_public.yaml")
        await loader.save()
        assert "echo" in await search("echo", group="public")
        assert await search("echo", group="other") == "No tools matched your query."

    @pytest.mark.asyncio
    async def test_grouped_tool_inaccessible_anonymous(self):
        _load("tools_grouped.yaml")
        await loader.save()
        assert await search("echo") == "No tools matched your query."

    @pytest.mark.asyncio
    async def test_ungrouped_display_name(self):
        _load("tools_public.yaml")
        await loader.save()
        result = await search("echo")
        assert "public.echo" in result
        assert "message: str" in result
        assert "Echoes back the provided message" in result


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
