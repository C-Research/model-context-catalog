from pathlib import Path

import pytest

from mcc.loader import Loader, load_file
from mcc.models import ToolModel

FIXTURES = Path(__file__).parent / "fixtures"


class TestLoadFile:
    def test_loads_ungrouped(self):
        tools = load_file(FIXTURES / "tools_ungrouped.yaml")
        assert len(tools) == 1
        assert tools[0].name == "echo"
        assert tools[0].group is None

    def test_loads_grouped(self):
        tools = load_file(FIXTURES / "tools_grouped.yaml")
        assert len(tools) == 1
        assert tools[0].name == "echo"
        assert tools[0].group == "example"

    def test_rejects_missing_tools_key(self):
        with pytest.raises(ValueError, match="expected a dict with a 'tools' key"):
            load_file(FIXTURES / "tools_missing_key.yaml")

    def test_rejects_missing_file(self):
        with pytest.raises(ValueError, match="not found"):
            load_file(FIXTURES / "nonexistent.yaml")


class TestLoader:
    def test_load_ungrouped(self):
        loader = Loader()
        loader.load(FIXTURES / "tools_ungrouped.yaml")
        assert "echo" in loader
        assert loader["echo"].group is None

    def test_load_grouped(self):
        loader = Loader()
        loader.load(FIXTURES / "tools_grouped.yaml")
        assert "example.echo" in loader
        assert loader["example.echo"].group == "example"

    def test_same_name_different_groups(self):
        loader = Loader()
        loader.load(FIXTURES / "tools_ungrouped.yaml")
        loader.load(FIXTURES / "tools_grouped.yaml")
        assert "echo" in loader
        assert "example.echo" in loader

    def test_duplicate_tool_raises(self):
        loader = Loader()
        loader.load(FIXTURES / "tools_ungrouped.yaml")
        with pytest.raises(ValueError, match="Duplicate tool"):
            loader.load(FIXTURES / "tools_ungrouped.yaml")

    def test_name_defaults_to_fn_name(self):
        loader = Loader()
        loader.load(FIXTURES / "tools_no_name.yaml")
        assert "echo" in loader

    def test_description_defaults_to_fn_docstring(self):
        loader = Loader()
        loader.load(FIXTURES / "tools_no_description.yaml")
        assert loader["doc_tool"].description == "A tool loaded from its docstring."

    def test_registry_entry_is_tool_model(self):
        loader = Loader()
        loader.load(FIXTURES / "tools_ungrouped.yaml")
        tool = loader["echo"]
        assert callable(tool.resolve_fn())
        assert tool.param_model is not None
        assert tool.description == "Echoes back the provided message"
        assert isinstance(tool.params, list)
        assert hasattr(tool, "group")

    def test_params_inferred_from_signature(self):
        loader = Loader()
        loader.load(FIXTURES / "tools_no_params.yaml")
        tool = loader["echo"]
        assert len(tool.params) == 1
        assert tool.params[0].name == "message"
        assert tool.params[0].type == "str"
        assert tool.params[0].required is True

    @pytest.mark.asyncio
    async def test_call_async_tool(self):
        loader = Loader()
        loader.load(FIXTURES / "tools_async.yaml")
        result = await loader["async_echo"].call(message="hello")
        assert result == ["hello"]
