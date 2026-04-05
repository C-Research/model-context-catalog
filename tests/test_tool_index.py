from pathlib import Path

import pytest
import pytest_asyncio

from mcc.loader import loader
from mcc.models import ToolModel
from mcc.db import ToolIndex

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _clean_loader():
    loader.clear()
    yield
    loader.clear()


@pytest_asyncio.fixture
async def _fresh_tool_index():
    async with ToolIndex() as idx:
        await idx.drop()
        await idx.create()
    await loader.save()
    yield
    async with ToolIndex() as idx:
        await idx.drop()


def _tool(name="echo", groups=None, description="Echoes back the provided message"):
    return ToolModel(
        fn="tests.example.echo",
        name=name,
        groups=groups or ["public"],
        description=description,
    )


class TestToolIndex:
    @pytest.mark.asyncio
    async def test_put_stored_fields(self, _fresh_tool_index):
        tool = _tool()
        async with ToolIndex() as idx:
            await idx.put(tool)
            results = await idx.search("echo")
        assert tool.key in [k for k, _ in results]

    @pytest.mark.asyncio
    async def test_search_by_name(self, _fresh_tool_index):
        tool = _tool(name="greet", description="Says hello")
        async with ToolIndex() as idx:
            await idx.put(tool)
            results = await idx.search("greet")
        assert tool.key in [k for k, _ in results]

    @pytest.mark.asyncio
    async def test_search_by_description(self, _fresh_tool_index):
        tool = _tool(name="greet", description="Says hello to someone")
        async with ToolIndex() as idx:
            await idx.put(tool)
            results = await idx.search("hello")
        assert tool.key in [k for k, _ in results]

    @pytest.mark.asyncio
    async def test_search_group_filter(self, _fresh_tool_index):
        public_tool = _tool(name="echo", groups=["public"], description="echo tool")
        admin_tool = _tool(name="echo", groups=["admin"], description="echo tool")
        async with ToolIndex() as idx:
            await idx.put(public_tool)
            await idx.put(admin_tool)
            public_results = await idx.search("echo", group="public")
            admin_results = await idx.search("echo", group="admin")
        public_keys = [k for k, _ in public_results]
        admin_keys = [k for k, _ in admin_results]
        assert public_tool.key in public_keys
        assert admin_tool.key not in public_keys
        assert admin_tool.key in admin_keys
        assert public_tool.key not in admin_keys

    @pytest.mark.asyncio
    async def test_search_fuzzy(self, _fresh_tool_index):
        tool = _tool(name="calculator", description="Computes math expressions")
        async with ToolIndex() as idx:
            await idx.put(tool)
            results = await idx.search("calculatr")  # typo
        assert tool.key in [k for k, _ in results]

    @pytest.mark.asyncio
    async def test_search_no_results(self, _fresh_tool_index):
        async with ToolIndex() as idx:
            results = await idx.search("zzz_nonexistent_xyz")
        assert results == []


class TestLoaderSave:
    @pytest.mark.asyncio
    async def test_save_reflects_loader(self, _fresh_tool_index):
        loader.load(FIXTURES / "tools_public.yaml")
        await loader.save()
        async with ToolIndex() as idx:
            results = await idx.search("echo")
        assert "public.echo" in [k for k, _ in results]

    @pytest.mark.asyncio
    async def test_stale_tools_removed_after_save(self, _fresh_tool_index):
        loader.load(FIXTURES / "tools_public.yaml")
        await loader.save()
        loader.clear()
        loader.load(FIXTURES / "tools_grouped.yaml")
        await loader.save()
        async with ToolIndex() as idx:
            results = await idx.search("echo")
        keys = [k for k, _ in results]
        assert "public.echo" not in keys
        assert "example.echo" in keys


class TestLoaderSearch:
    @pytest.mark.asyncio
    async def test_returns_tool_models(self, _fresh_tool_index):
        loader.load(FIXTURES / "tools_public.yaml")
        await loader.save()
        results = await loader.search("echo")
        assert len(results) == 1
        tool, score = results[0]
        assert isinstance(tool, ToolModel)
        assert tool.key == "public.echo"
        assert isinstance(score, float)

    @pytest.mark.asyncio
    async def test_skips_keys_not_in_loader(self, _fresh_tool_index):
        ghost = _tool(name="ghost", groups=["public"], description="ghost tool")
        async with ToolIndex() as idx:
            await idx.put(ghost)
        # ghost is in ES but not in loader — should be skipped
        results = await loader.search("ghost")
        assert all(tool.key != "public.ghost" for tool, _ in results)
