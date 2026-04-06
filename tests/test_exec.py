import sys

import pytest
from jinja2 import UndefinedError

from mcc.loader import loader
from mcc.models import ToolModel


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

    async def test_list_is_quoted_and_joined(self):
        from mcc.exec import _quote_filter

        result = _quote_filter(["a.txt", "b c.txt"])
        assert result == "a.txt 'b c.txt'"

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
