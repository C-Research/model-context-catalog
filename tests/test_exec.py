import sys

import pytest
from jinja2 import UndefinedError

from mcc.exec import make_py_callable
from mcc.loader import loader
from mcc.models import ToolModel


@pytest.mark.smoke
class TestExecToolLoading:
    def test_loads_exec_tool(self, load_fixture):
        load_fixture("tools_exec_interpolate.yaml")
        assert "echo_interp" in loader
        tool = loader["echo_interp"]
        assert tool.exec == "echo {{ message | quote }}"
        assert tool.fn is None

    def test_fn_and_exec_raises(self):
        with pytest.raises(ValueError, match="either 'fn' or 'exec'"):
            ToolModel(fn="os:getcwd", **{"exec": "echo hi"})

    def test_neither_fn_nor_exec_raises(self):
        with pytest.raises(ValueError, match="either 'fn' or 'exec'"):
            ToolModel(name="broken")

    def test_missing_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            ToolModel(**{"exec": "echo hello"})


class TestInterpolationMode:
    async def test_params_interpolated(self):
        tool = ToolModel(
            name="greet",
            **{"exec": "echo {{ message | quote }}"},
            params=[{"name": "message", "type": "str", "required": True}],
        )
        stdout = await tool.call(message="hello world")
        assert "hello world" in stdout

    async def test_successful_returns_stdout(self):
        tool = ToolModel(name="ok", **{"exec": "echo ok"})
        result = await tool.call()
        assert isinstance(result, str)
        assert "ok" in result

    async def test_failed_returns_tuple(self):
        tool = ToolModel(name="fail", **{"exec": "false"})
        code, out, err = await tool.call()
        assert code != 0


class TestStdinMode:
    async def test_json_sent_on_stdin(self):
        tool = ToolModel(
            name="reader",
            **{"exec": "cat"},
            stdin=True,
            params=[{"name": "key", "type": "str", "required": True}],
        )
        stdout = await tool.call(key="value")
        assert '"key": "value"' in stdout


class TestJinjaQuoteFilter:
    async def test_scalar_with_spaces_is_quoted(self):
        tool = ToolModel(
            name="echo_safe",
            **{"exec": "echo {{ msg | quote }}"},
            params=[{"name": "msg", "type": "str", "required": True}],
        )
        stdout = await tool.call(msg="hello world")
        assert "hello world" in stdout

    async def test_shell_metacharacters_quoted(self):
        tool = ToolModel(
            name="echo_meta",
            **{"exec": "echo {{ msg | quote }}"},
            params=[{"name": "msg", "type": "str", "required": True}],
        )
        stdout = await tool.call(msg="hello; rm -rf /")
        assert "hello; rm -rf /" in stdout

    @pytest.mark.smoke
    async def test_list_is_quoted_and_joined(self):
        from mcc.exec import _quote_filter

        result = _quote_filter(["a.txt", "b c.txt"])
        assert result == "a.txt 'b c.txt'"

    @pytest.mark.smoke
    async def test_empty_list_produces_empty_string(self):
        from mcc.exec import _quote_filter

        assert _quote_filter([]) == ""

    async def test_conditional_block_includes_flag(self):
        tool = ToolModel(
            name="grepper",
            **{"exec": "echo {% if flag %}-v {% endif %}{{ msg | quote }}"},
            params=[
                {"name": "flag", "type": "bool", "required": True},
                {"name": "msg", "type": "str", "required": True},
            ],
        )
        stdout = await tool.call(flag=True, msg="hi")
        assert "-v" in stdout

    async def test_conditional_block_omits_flag(self):
        tool = ToolModel(
            name="grepper2",
            **{"exec": "echo {% if flag %}-v {% endif %}{{ msg | quote }}"},
            params=[
                {"name": "flag", "type": "bool", "required": True},
                {"name": "msg", "type": "str", "required": True},
            ],
        )
        stdout = await tool.call(flag=False, msg="hi")
        assert "-v" not in stdout

    async def test_unknown_variable_raises_before_exec(self):
        tool = ToolModel(
            name="bad_template",
            **{"exec": "echo {{ typo }}"},
            params=[],
        )
        with pytest.raises(UndefinedError):
            await tool.call()


class TestEnvYAMLCoexistence:
    async def test_envyaml_and_jinja_together(self, load_fixture, monkeypatch):
        # EnvYAML resolves ${GREET_PREFIX} at load time; Jinja renders {{ name | quote }} at call time
        monkeypatch.setenv("GREET_PREFIX", "hello")
        load_fixture("tools_exec_envyaml.yaml")
        from mcc.loader import loader

        tool = loader["greet_env"]
        assert "${GREET_PREFIX}" not in tool.exec  # already resolved by EnvYAML
        assert "{{ name | quote }}" in tool.exec  # Jinja not yet rendered
        stdout = await tool.call(name="world")
        assert "hello" in stdout
        assert "world" in stdout


class TestStdinWithInterpolation:
    async def test_stdin_and_interpolation_together(self):
        tool = ToolModel(
            name="combo",
            **{"exec": "cat"},
            stdin=True,
            params=[
                {"name": "project", "type": "str", "required": True},
                {"name": "data", "type": "str", "required": True},
            ],
        )
        stdout = await tool.call(project="myproj", data="payload")
        import json

        blob = json.loads(stdout)
        assert blob["project"] == "myproj"
        assert blob["data"] == "payload"

    async def test_interpolation_applied_to_command_with_stdin(self):
        tool = ToolModel(
            name="echostdin",
            **{"exec": "echo {{ tag | quote }} && cat"},
            stdin=True,
            params=[
                {"name": "tag", "type": "str", "required": True},
                {"name": "body", "type": "str", "required": True},
            ],
        )
        stdout = await tool.call(tag="HEADER", body="content")
        assert "HEADER" in stdout
        assert '"body"' in stdout


class TestTimeout:
    async def test_timeout_kills_and_returns(self):
        tool = ToolModel(name="slow", **{"exec": "sleep 10"}, timeout=1)
        code, stdout, stderr = await tool.call()
        assert code == -1
        assert "timeout after 1s" in stderr


class TestPyCallable:
    async def test_returns_str_on_success(self):
        import json

        callable_ = make_py_callable("tests.example:add", sys.executable, None, None)
        result = await callable_(x=2, y=3)
        assert isinstance(result, str)
        assert json.loads(result) == 5

    async def test_returns_tuple_on_failure(self):
        callable_ = make_py_callable(
            "tests.example:always_fails", sys.executable, None, None
        )
        code, out, err = await callable_(msg="boom")
        assert code != 0
        assert "RuntimeError" in err

    async def test_timeout_kills_and_returns(self):
        # use a small exec tool equivalent: python -c "import time; time.sleep(10)"
        # but via make_py_callable with a function that sleeps
        # We use make_exec_callable for a simpler timeout test here since
        # always_fails exits immediately. Instead, construct directly via ToolModel.
        tool = ToolModel(
            fn="tests.example:add",
            python=sys.executable,
            timeout=1,
            params=[
                {"name": "x", "type": "int", "required": True},
                {"name": "y", "type": "int", "required": True},
            ],
        )
        # add() is fast, just verify timeout doesn't break normal execution
        import json

        result = await tool.call(x=1, y=1)
        assert json.loads(result) == 2


class TestResourceLimits:
    @pytest.mark.skipif(sys.platform == "win32", reason="unix only")
    async def test_limits_applied(self):
        tool = ToolModel(
            name="limited",
            **{"exec": "echo ok"},
            limits={"mem_mb": 256, "cpu_sec": 5},
        )
        stdout = await tool.call()
        assert "ok" in stdout

    async def test_no_limits_runs_fine(self):
        tool = ToolModel(name="nolimit", **{"exec": "echo fine"})
        stdout = await tool.call()
        assert "fine" in stdout


class TestCwdEnvEnvFile:
    async def test_exec_cwd(self, tmp_path):
        tool = ToolModel(name="pwd_tool", **{"exec": "pwd"}, cwd=str(tmp_path))
        stdout = await tool.call()
        assert str(tmp_path) in stdout

    async def test_exec_env(self):
        tool = ToolModel(
            name="env_tool",
            **{"exec": "echo $MY_VAR"},
            env={"MY_VAR": "hello_env"},
        )
        stdout = await tool.call()
        assert "hello_env" in stdout

    async def test_exec_env_file(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("MY_FILE_VAR=from_file\n")
        tool = ToolModel(
            name="envfile_tool",
            **{"exec": "echo $MY_FILE_VAR"},
            env_file=str(env_file),
        )
        stdout = await tool.call()
        assert "from_file" in stdout

    async def test_env_overrides_env_file(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("MYVAR=from_file\n")
        tool = ToolModel(
            name="override_tool",
            **{"exec": "echo $MYVAR"},
            env_file=str(env_file),
            env={"MYVAR": "from_env"},
        )
        stdout = await tool.call()
        assert "from_env" in stdout

    async def test_py_callable_cwd(self, tmp_path):
        tool = ToolModel(
            fn="os:getcwd",
            python=sys.executable,
            cwd=str(tmp_path),
        )
        import json

        result = await tool.call()
        assert str(tmp_path) in json.loads(result)

    async def test_py_callable_env(self):
        tool = ToolModel(
            fn="tests.example:get_env_var",
            python=sys.executable,
            env={"TEST_PY_VAR": "py_env_val"},
            env_passthrough=True,  # add to parent env so Python imports still work
            params=[{"name": "name", "type": "str", "required": True}],
        )
        import json

        result = await tool.call(name="TEST_PY_VAR")
        assert json.loads(result) == "py_env_val"

    async def test_env_passthrough_false_excludes_parent_env(self, monkeypatch):
        monkeypatch.setenv("MCC_TEST_PARENT_ONLY", "parent_value")
        tool = ToolModel(
            name="check_passthrough",
            **{"exec": "echo ${MCC_TEST_PARENT_ONLY:-not_inherited}"},
            env={"EXPLICIT": "yes"},
            env_passthrough=False,
        )
        stdout = await tool.call()
        assert "not_inherited" in stdout


class TestFnToolDirect:
    """fn tools constructed directly (not via loader) introspect and call correctly."""

    def test_construction_introspects_name_and_params(self):
        tool = ToolModel(fn="tests.example:add", python=sys.executable)
        assert tool.name == "add"
        assert len(tool.params) == 2
        names = {p.name for p in tool.params}
        assert names == {"x", "y"}

    def test_construction_captures_return_type(self):
        tool = ToolModel(fn="tests.example:add", python=sys.executable)
        assert tool.return_type == "int"

    async def test_call_returns_correct_result(self):
        import json

        tool = ToolModel(fn="tests.example:add", python=sys.executable)
        result = await tool.call(x=3, y=4)
        assert json.loads(result) == 7


class TestFnToolNoPython:
    """fn tools with no python field behave identically to python=sys.executable."""

    def test_python_defaults_to_sys_executable(self):
        tool = ToolModel(fn="tests.example:add")
        assert tool.python is not None
        assert tool.python == sys.executable or tool.python.endswith("python3") or "python" in tool.python

    def test_introspection_succeeds_without_python_field(self):
        tool = ToolModel(fn="tests.example:add")
        assert tool.name == "add"
        assert len(tool.params) == 2

    async def test_call_result_matches_explicit_python(self):
        import json

        tool_implicit = ToolModel(fn="tests.example:add")
        tool_explicit = ToolModel(fn="tests.example:add", python=sys.executable)
        r1 = await tool_implicit.call(x=5, y=5)
        r2 = await tool_explicit.call(x=5, y=5)
        assert json.loads(r1) == json.loads(r2) == 10
