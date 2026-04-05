import sys

import pytest

from mcc.loader import loader
from mcc.models import ToolModel


class TestExecToolLoading:
    def test_loads_exec_tool(self, load_fixture):
        load_fixture("tools_exec_interpolate.yaml")
        assert "echo_interp" in loader
        tool = loader["echo_interp"]
        assert tool.exec == "echo {message}"
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
            **{"exec": "echo {message}"},
            params=[{"name": "message", "type": "str", "required": True}],
        )
        code, stdout, stderr = await tool.call(message="hello world")
        assert code == 0
        assert "hello world" in stdout

    async def test_successful_returns_zero(self):
        tool = ToolModel(name="ok", **{"exec": "true"})
        code, stdout, stderr = await tool.call()
        assert code == 0

    async def test_failed_returns_nonzero(self):
        tool = ToolModel(name="fail", **{"exec": "false"})
        code, stdout, stderr = await tool.call()
        assert code != 0


class TestStdinMode:
    async def test_json_sent_on_stdin(self):
        tool = ToolModel(
            name="reader",
            **{"exec": "cat"},
            stdin=True,
            params=[{"name": "key", "type": "str", "required": True}],
        )
        code, stdout, stderr = await tool.call(key="value")
        assert code == 0
        assert '"key": "value"' in stdout


class TestShlexQuoting:
    async def test_shell_metacharacters_escaped(self):
        tool = ToolModel(
            name="echo_safe",
            **{"exec": "echo {msg}"},
            params=[{"name": "msg", "type": "str", "required": True}],
        )
        code, stdout, stderr = await tool.call(msg="hello; rm -rf /")
        assert code == 0
        assert "hello; rm -rf /" in stdout
        assert "rm" not in stderr


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
        code, stdout, stderr = await tool.call(project="myproj", data="payload")
        assert code == 0
        import json

        blob = json.loads(stdout)
        assert blob["project"] == "myproj"
        assert blob["data"] == "payload"

    async def test_interpolation_applied_to_command_with_stdin(self):
        tool = ToolModel(
            name="echostdin",
            **{"exec": "echo {tag} && cat"},
            stdin=True,
            params=[
                {"name": "tag", "type": "str", "required": True},
                {"name": "body", "type": "str", "required": True},
            ],
        )
        code, stdout, stderr = await tool.call(tag="HEADER", body="content")
        assert code == 0
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
        code, stdout, stderr = await tool.call()
        assert code == 0
        assert "ok" in stdout

    async def test_no_limits_runs_fine(self):
        tool = ToolModel(name="nolimit", **{"exec": "echo fine"})
        code, stdout, stderr = await tool.call()
        assert code == 0
        assert "fine" in stdout
