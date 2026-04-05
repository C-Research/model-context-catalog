from pathlib import Path

import pytest
import pytest_asyncio

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
    async def test_matches_by_name(self):
        _load("tools_ungrouped.yaml")
        await loader.save()
        result = await search("echo")
        assert "echo" in result
        assert "Echoes back" in result

    async def test_no_match(self):
        _load("tools_ungrouped.yaml")
        await loader.save()
        result = await search("zzz_nonexistent", min_score=999.0)
        assert result.startswith("No tools matched your query.")

    async def test_grouped_tool_inaccessible_anonymous(self):
        _load("tools_grouped.yaml")
        await loader.save()
        result = await search("echo")
        assert result.startswith("No tools matched your query.")

    async def test_ungrouped_display_name(self):
        _load("tools_ungrouped.yaml")
        await loader.save()
        result = await search("echo")
        assert "echo" in result
        assert "message (str" in result
        assert "Echoes back the provided message" in result


class TestExecute:
    async def test_execute_public_tool(self):
        _load("tools_ungrouped.yaml")
        result = await execute("echo", {"message": "hi"})
        assert result == ["hi"]

    async def test_execute_grouped_tool_unauthorized(self):
        _load("tools_grouped.yaml")
        result = await execute("example.echo", {"message": "hi"})
        assert result.startswith("Unauthorized")

    async def test_execute_unknown_tool(self):
        _load("tools_ungrouped.yaml")
        result = await execute("nonexistent", {})
        assert "Unknown tool" in result

    async def test_execute_validation_error(self):
        _load("tools_ungrouped.yaml")
        result = await execute("echo", {})
        assert "Validation error" in result
