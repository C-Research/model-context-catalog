import json
import sys
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcc.loader import Loader, load_file
from mcc.models import ToolModel

FIXTURES = Path(__file__).parent / "fixtures"
CONTRIB = Path(__file__).parents[1] / "mcc" / "contrib"


@pytest.mark.smoke
class TestLoadFile:
    def test_loads_ungrouped(self):
        tools = load_file(FIXTURES / "tools_ungrouped.yaml")
        assert len(tools) == 1
        assert tools[0].name == "echo"
        assert tools[0].groups == []

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
    @pytest.mark.smoke
    def test_load_ungrouped(self):
        loader = Loader()
        loader.load(FIXTURES / "tools_ungrouped.yaml")
        assert "echo" in loader
        assert loader["echo"].groups == []

    @pytest.mark.smoke
    def test_load_grouped(self):
        loader = Loader()
        loader.load(FIXTURES / "tools_grouped.yaml")
        assert "example.echo" in loader
        assert loader["example.echo"].groups == ["example"]

    @pytest.mark.smoke
    def test_same_name_different_groups(self):
        loader = Loader()
        loader.load(FIXTURES / "tools_ungrouped.yaml")
        loader.load(FIXTURES / "tools_grouped.yaml")
        assert "echo" in loader
        assert "example.echo" in loader

    @pytest.mark.smoke
    def test_duplicate_tool_raises(self):
        loader = Loader()
        loader.load(FIXTURES / "tools_ungrouped.yaml")
        with pytest.raises(ValueError, match="Duplicate tool"):
            loader.load(FIXTURES / "tools_ungrouped.yaml")

    @pytest.mark.smoke
    def test_name_defaults_to_fn_name(self):
        loader = Loader()
        loader.load(FIXTURES / "tools_no_name.yaml")
        assert "echo" in loader

    def test_description_defaults_to_fn_docstring(self):
        loader = Loader()
        loader.load(FIXTURES / "tools_no_description.yaml")
        assert loader["doc_tool"].description == "A tool loaded from its docstring."

    @pytest.mark.smoke
    def test_registry_entry_is_tool_model(self):
        loader = Loader()
        loader.load(FIXTURES / "tools_ungrouped.yaml")
        tool = loader["echo"]
        assert callable(tool.callable)
        assert tool.param_model is not None
        assert tool.description == "Echoes back the provided message"
        assert isinstance(tool.params, list)
        assert hasattr(tool, "groups")

    def test_params_inferred_from_signature(self):
        loader = Loader()
        loader.load(FIXTURES / "tools_no_params.yaml")
        tool = loader["echo"]
        assert len(tool.params) == 1
        assert tool.params[0].name == "message"
        assert tool.params[0].type == "str"
        assert tool.params[0].required is True

    async def test_call_async_tool(self):
        loader = Loader()
        loader.load(FIXTURES / "tools_async.yaml")
        result = await loader["async_echo"].call(message="hello")
        assert json.loads(result) == ["hello"]


class TestParamOverride:
    def setup_method(self):
        self.loader = Loader()
        self.loader.load(FIXTURES / "tools_override.yaml")
        self.tool = self.loader["echo_with_flag"]

    @pytest.mark.smoke
    def test_override_param_has_override(self):
        flag_param = next(p for p in self.tool.params if p.name == "flag")
        assert flag_param.has_override is True
        assert flag_param.override is True

    @pytest.mark.smoke
    def test_non_override_param_has_no_override(self):
        message_param = next(p for p in self.tool.params if p.name == "message")
        assert message_param.has_override is False

    @pytest.mark.smoke
    def test_override_param_excluded_from_param_model(self):
        assert "flag" not in self.tool.param_model.model_fields

    @pytest.mark.smoke
    def test_override_param_excluded_from_signature(self):
        assert "- flag" not in self.tool.signature

    async def test_override_value_is_injected(self):
        result = await self.tool.call(message="hello")
        assert json.loads(result) == {"message": "hello", "flag": True}

    async def test_override_silently_replaces_caller_value(self):
        # caller passing flag should be silently ignored — override wins
        result = await self.tool.call(message="hello", flag=False)
        assert json.loads(result) == {"message": "hello", "flag": True}

    @pytest.mark.smoke
    def test_no_override_is_default(self):
        from mcc.models import ParamModel

        p = ParamModel(name="x")
        assert p.has_override is False


class TestEnvVarSubstitution:
    def test_env_var_substituted_in_description(self, monkeypatch):
        monkeypatch.setenv("MCC_TEST_DESCRIPTION", "Injected from environment")
        tools = load_file(FIXTURES / "tools_env_var.yaml")
        assert tools[0].description == "Injected from environment"

    def test_missing_env_var_leaves_literal(self, monkeypatch):
        monkeypatch.delenv("MCC_TEST_DESCRIPTION", raising=False)
        tools = load_file(FIXTURES / "tools_env_var.yaml")
        assert tools[0].description == "$MCC_TEST_DESCRIPTION"


class TestIsolatedPython:
    def test_params_auto_populated_via_introspection(self):
        tool = ToolModel(fn="tests.example:add", python=sys.executable)
        assert len(tool.params) == 2
        names = {p.name for p in tool.params}
        assert names == {"x", "y"}
        assert all(p.type == "int" for p in tool.params)
        assert all(p.required for p in tool.params)

    def test_name_populated_via_introspection(self):
        tool = ToolModel(fn="tests.example:add", python=sys.executable)
        assert tool.name == "add"

    def test_description_populated_from_docstring(self):
        tool = ToolModel(fn="tests.example:documented_tool", python=sys.executable)
        assert "docstring" in tool.description.lower()

    def test_explicit_params_skip_introspection(self):
        tool = ToolModel(
            fn="tests.example:add",
            python=sys.executable,
            name="my_add",
            params=[{"name": "x", "type": "str", "required": True}],
        )
        assert len(tool.params) == 1
        assert tool.params[0].type == "str"

    def test_unknown_interpreter_raises(self):
        with pytest.raises(ValueError, match="not found"):
            ToolModel(fn="tests.example:add", python="/nonexistent/python999")

    def test_python_with_exec_raises(self):
        with pytest.raises(ValueError, match="'python' can only be used with 'fn'"):
            ToolModel(
                name="bad",
                **{"exec": "echo hi"},
                python=sys.executable,
            )

    async def test_call_returns_json_result(self):
        tool = ToolModel(fn="tests.example:add", python=sys.executable)
        result = await tool.call(x=10, y=32)
        assert json.loads(result) == 42

    async def test_async_fn_end_to_end(self):
        tool = ToolModel(fn="tests.example:async_add", python=sys.executable)
        result = await tool.call(x=7, y=3)
        assert json.loads(result) == 10


@pytest.mark.smoke
class TestBatchIntrospectOptimization:
    def _mock_introspect_result(self, *entries):
        """Build a mock subprocess.CompletedProcess for a batch introspect call."""
        mock = MagicMock()
        mock.returncode = 0
        mock.stderr = ""
        mock.stdout = json.dumps(list(entries))
        return mock

    def test_single_interpreter_calls_subprocess_once(self, tmp_path):
        yaml_file = tmp_path / "tools.yaml"
        yaml_file.write_text(
            textwrap.dedent("""\
                tools:
                  - fn: tests.example:add
                  - fn: tests.example:echo
            """)
        )

        mock_result = self._mock_introspect_result(
            {
                "fn_path": "tests.example:add",
                "name": "add",
                "doc": "",
                "params": [
                    {
                        "name": "x",
                        "type": "int",
                        "required": True,
                        "default": None,
                        "description": "",
                    },
                    {
                        "name": "y",
                        "type": "int",
                        "required": True,
                        "default": None,
                        "description": "",
                    },
                ],
                "return_type": "int",
            },
            {
                "fn_path": "tests.example:echo",
                "name": "echo",
                "doc": "",
                "params": [
                    {
                        "name": "message",
                        "type": "str",
                        "required": True,
                        "default": None,
                        "description": "",
                    },
                ],
                "return_type": "list[str]",
            },
        )

        with patch("mcc.loader.subprocess.run", return_value=mock_result) as mock_run:
            tools = load_file(yaml_file)

        assert mock_run.call_count == 1
        cmd = mock_run.call_args[0][0]
        assert "introspect" in cmd
        assert "tests.example:add" in cmd
        assert "tests.example:echo" in cmd
        assert len(tools) == 2

    def test_explicit_params_skip_batch_prepass(self, tmp_path):
        yaml_file = tmp_path / "tools.yaml"
        yaml_file.write_text(
            textwrap.dedent("""\
                tools:
                  - fn: tests.example:add
                    name: my_add
                    description: adds two numbers
                    params:
                      - name: x
                        type: int
                        required: true
                      - name: y
                        type: int
                        required: true
            """)
        )

        with patch("mcc.loader.subprocess.run") as mock_run:
            tools = load_file(yaml_file)

        mock_run.assert_not_called()
        assert len(tools) == 1
        assert tools[0].name == "my_add"


@pytest.mark.smoke
class TestGlobLoading:
    _TOOL_YAML = """\
tools:
  - name: {name}
    fn: tests.example.echo
    description: test tool
    params:
      - name: message
        type: str
        required: true
"""

    def _write(self, path: Path, name: str) -> None:
        path.write_text(self._TOOL_YAML.format(name=name))

    def test_flat_glob(self, tmp_path):
        self._write(tmp_path / "a.yaml", "tool_a")
        self._write(tmp_path / "b.yaml", "tool_b")
        loader = Loader()
        loader.load(str(tmp_path / "*.yaml"))
        assert "tool_a" in loader
        assert "tool_b" in loader

    def test_recursive_glob(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        self._write(tmp_path / "top.yaml", "top_tool")
        self._write(sub / "nested.yaml", "nested_tool")
        loader = Loader()
        loader.load(str(tmp_path / "**" / "*.yaml"))
        assert "top_tool" in loader
        assert "nested_tool" in loader

    def test_no_matches_loads_nothing(self, tmp_path):
        loader = Loader()
        loader.load(str(tmp_path / "*.yaml"))
        assert len(loader) == 0

    def test_glob_pattern_stored_for_reload(self, tmp_path):
        self._write(tmp_path / "a.yaml", "tool_a")
        pattern = str(tmp_path / "*.yaml")
        loader = Loader()
        loader.load(pattern)
        assert pattern in loader.paths

    def test_glob_picks_up_new_files_on_reload(self, tmp_path):
        self._write(tmp_path / "a.yaml", "tool_a")
        pattern = str(tmp_path / "*.yaml")
        loader = Loader()
        loader.load(pattern)
        assert len(loader) == 1
        # add a second file — reload should pick it up
        self._write(tmp_path / "b.yaml", "tool_b")
        loader.clear()
        loader.load(pattern)
        assert "tool_a" in loader
        assert "tool_b" in loader


class TestContribLoading:
    def test_contrib_fn_loads_via_subprocess(self):
        # mcc.contrib.system is importable in the test env — verifies the subprocess path works
        tools = load_file(CONTRIB / "system.yaml")
        tool_map = {t.name: t for t in tools}
        assert "get_env" in tool_map
        get_env = tool_map["get_env"]
        assert len(get_env.params) > 0
        assert any(p.name == "keys" for p in get_env.params)


class TestFileLevelEnv:
    def test_file_envfile_inherited_by_tools_without_own(self):
        tools = load_file(FIXTURES / "tools_file_envfile.yaml")
        tool_map = {t.name: t for t in tools}
        assert tool_map["tool_inherits"].env_file == "some.env"

    def test_file_envfile_does_not_override_per_tool_envfile(self):
        tools = load_file(FIXTURES / "tools_file_envfile.yaml")
        tool_map = {t.name: t for t in tools}
        assert tool_map["tool_own_envfile"].env_file == "other.env"

    def test_file_env_inherited_by_tools_without_own(self):
        tools = load_file(FIXTURES / "tools_file_env_block.yaml")
        tool_map = {t.name: t for t in tools}
        assert tool_map["tool_inherits_env"].env == {
            "KEY_A": "file_value_a",
            "KEY_B": "file_value_b",
        }

    def test_file_env_merges_with_per_tool_env_tool_wins(self):
        tools = load_file(FIXTURES / "tools_file_env_block.yaml")
        tool_map = {t.name: t for t in tools}
        merged = tool_map["tool_merges_env"].env
        assert merged["KEY_A"] == "tool_value_a"  # tool wins over file
        assert merged["KEY_B"] == "file_value_b"  # inherited from file
        assert merged["KEY_C"] == "tool_value_c"  # tool-only key preserved

    def test_no_file_env_loads_without_change(self):
        # Regression: YAML files without top-level env_file/env still load normally
        tools = load_file(FIXTURES / "tools_ungrouped.yaml")
        assert len(tools) == 1
        assert tools[0].name == "echo"
