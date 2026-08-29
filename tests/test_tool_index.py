from mcc.loader import loader
from mcc.models import ToolModel


def _tool(name="echo", groups=None, description="Echoes back the provided message"):
    return ToolModel(
        fn="tests.example.echo",
        name=name,
        groups=groups or [],
        description=description,
    )


class TestToolIndex:
    async def test_put_stored_fields(self, tool_idx):
        tool = _tool()
        await tool_idx.index_tool(tool)
        results = await tool_idx.query("echo")
        assert tool.key in [k for k, _ in results]

    async def test_search_by_name(self, tool_idx):
        tool = _tool(name="greet", description="Says hello")
        await tool_idx.index_tool(tool)
        results = await tool_idx.query("greet")
        assert tool.key in [k for k, _ in results]

    async def test_search_by_description(self, tool_idx):
        tool = _tool(name="greet", description="Says hello to someone")
        await tool_idx.index_tool(tool)
        results = await tool_idx.query("hello")
        assert tool.key in [k for k, _ in results]

    async def test_search_fuzzy(self, tool_idx):
        tool = _tool(name="calculator", description="Computes math expressions")
        await tool_idx.index_tool(tool)
        results = await tool_idx.query("calculatr")  # typo
        assert tool.key in [k for k, _ in results]

    async def test_search_no_results(self, tool_idx):
        results = await tool_idx.query("zzz_nonexistent_xyz")
        assert results == []


class TestToolIndexGroupsFilter:
    async def test_query_without_groups_returns_all_matches(self, tool_idx):
        public = _tool(name="echo", groups=[])
        grouped = _tool(name="echo2", groups=["example"])
        await tool_idx.index_tool(public)
        await tool_idx.index_tool(grouped)
        results = await tool_idx.query("echo")
        keys = {k for k, _ in results}
        assert public.key in keys
        assert grouped.key in keys

    async def test_query_with_groups_restricts_to_matching_tools(self, tool_idx):
        public = _tool(name="echo", groups=[])
        grouped = _tool(name="echo2", groups=["example"])
        await tool_idx.index_tool(public)
        await tool_idx.index_tool(grouped)
        results = await tool_idx.query("echo", groups=["example"])
        keys = {k for k, _ in results}
        assert keys == {grouped.key}

    async def test_query_with_nonmatching_groups_returns_empty(self, tool_idx):
        tool = _tool(name="echo", groups=["example"])
        await tool_idx.index_tool(tool)
        results = await tool_idx.query("echo", groups=["nonexistent"])
        assert results == []


class TestLoaderSave:
    async def test_save_reflects_loader(self, tool_idx, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        await loader.save()
        results = await tool_idx.query("echo")
        assert "echo" in [k for k, _ in results]

    async def test_stale_tools_removed_after_save(self, tool_idx, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        await loader.save()
        loader.clear()
        load_fixture("tools_grouped.yaml")
        await loader.save()
        results = await tool_idx.query("echo")
        keys = [k for k, _ in results]
        assert "echo" not in keys
        assert "example.echo" in keys


class TestLoaderSearch:
    async def test_returns_tool_models(self, tool_idx, load_fixture):
        load_fixture("tools_ungrouped.yaml")
        await loader.save()
        results = await loader.search("echo")
        assert len(results) == 1
        tool, score = results[0]
        assert isinstance(tool, ToolModel)
        assert tool.key == "echo"
        assert isinstance(score, float)

    async def test_skips_keys_not_in_loader(self, tool_idx):
        ghost = _tool(name="ghost", groups=[], description="ghost tool")
        await tool_idx.index_tool(ghost)
        # ghost is in ES but not in loader — should be skipped
        results = await loader.search("ghost")
        assert all(tool.key != "ghost" for tool, _ in results)


class TestLoaderSearchGroupsFilter:
    async def test_no_groups_returns_all_matches(self, tool_idx, load_fixture):
        load_fixture("tools_ungrouped.yaml", "tools_grouped.yaml")
        await loader.save()
        results = await loader.search("echo")
        keys = {tool.key for tool, _ in results}
        assert keys == {"echo", "example.echo"}

    async def test_groups_filter_restricts_results(self, tool_idx, load_fixture):
        load_fixture("tools_ungrouped.yaml", "tools_grouped.yaml")
        await loader.save()
        results = await loader.search("echo", groups={"example"})
        keys = {tool.key for tool, _ in results}
        assert keys == {"example.echo"}

    async def test_nonmatching_groups_returns_empty(self, tool_idx, load_fixture):
        load_fixture("tools_ungrouped.yaml", "tools_grouped.yaml")
        await loader.save()
        results = await loader.search("echo", groups={"nonexistent"})
        assert results == []
