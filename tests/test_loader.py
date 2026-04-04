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
        assert tools[0].groups == ["public"]

    def test_loads_grouped(self):
        tools = load_file(FIXTURES / "tools_grouped.yaml")
        assert len(tools) == 1
        assert tools[0].name == "echo"
        assert tools[0].groups == ["example"]

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
        assert "public.echo" in loader
        assert loader["public.echo"].groups == ["public"]

    def test_load_grouped(self):
        loader = Loader()
        loader.load(FIXTURES / "tools_grouped.yaml")
        assert "example.echo" in loader
        assert loader["example.echo"].groups == ["example"]

    def test_same_name_different_groups(self):
        loader = Loader()
        loader.load(FIXTURES / "tools_ungrouped.yaml")
        loader.load(FIXTURES / "tools_grouped.yaml")
        assert "public.echo" in loader
        assert "example.echo" in loader

    def test_duplicate_tool_raises(self):
        loader = Loader()
        loader.load(FIXTURES / "tools_ungrouped.yaml")
        with pytest.raises(ValueError, match="Duplicate tool"):
            loader.load(FIXTURES / "tools_ungrouped.yaml")

    def test_name_defaults_to_fn_name(self):
        loader = Loader()
        loader.load(FIXTURES / "tools_no_name.yaml")
        assert "public.echo" in loader

    def test_description_defaults_to_fn_docstring(self):
        loader = Loader()
        loader.load(FIXTURES / "tools_no_description.yaml")
        assert loader["public.doc_tool"].description == "A tool loaded from its docstring."

    def test_registry_entry_is_tool_model(self):
        loader = Loader()
        loader.load(FIXTURES / "tools_ungrouped.yaml")
        tool = loader["public.echo"]
        assert callable(tool.resolve_fn())
        assert tool.param_model is not None
        assert tool.description == "Echoes back the provided message"
        assert isinstance(tool.params, list)
        assert hasattr(tool, "groups")

    def test_params_inferred_from_signature(self):
        loader = Loader()
        loader.load(FIXTURES / "tools_no_params.yaml")
        tool = loader["public.echo"]
        assert len(tool.params) == 1
        assert tool.params[0].name == "message"
        assert tool.params[0].type == "str"
        assert tool.params[0].required is True

    @pytest.mark.asyncio
    async def test_call_async_tool(self):
        loader = Loader()
        loader.load(FIXTURES / "tools_async.yaml")
        result = await loader["public.async_echo"].call(message="hello")
        assert result == ["hello"]


class TestParamOverride:
    def setup_method(self):
        self.loader = Loader()
        self.loader.load(FIXTURES / "tools_override.yaml")
        self.tool = self.loader["public.echo_with_flag"]

    def test_override_param_has_override(self):
        flag_param = next(p for p in self.tool.params if p.name == "flag")
        assert flag_param.has_override is True
        assert flag_param.override is True

    def test_non_override_param_has_no_override(self):
        message_param = next(p for p in self.tool.params if p.name == "message")
        assert message_param.has_override is False

    def test_override_param_excluded_from_param_model(self):
        assert "flag" not in self.tool.param_model.model_fields

    def test_override_param_excluded_from_signature(self):
        assert "flag:" not in self.tool.signature and "flag?" not in self.tool.signature

    @pytest.mark.asyncio
    async def test_override_value_is_injected(self):
        result = await self.tool.call(message="hello")
        assert result == {"message": "hello", "flag": True}

    @pytest.mark.asyncio
    async def test_override_silently_replaces_caller_value(self):
        # caller passing flag should be silently ignored — override wins
        result = await self.tool.call(message="hello", flag=False)
        assert result == {"message": "hello", "flag": True}

    def test_no_override_is_default(self):
        from mcc.models import ParamModel
        p = ParamModel(name="x")
        assert p.has_override is False
