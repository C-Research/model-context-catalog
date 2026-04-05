from mcc.contrib.subprocess import bash


class TestBash:
    async def test_captures_stdout(self):
        code, out, err = await bash("echo hello")
        assert code == 0
        assert out.strip() == "hello"

    async def test_captures_stderr(self):
        code, out, err = await bash("echo err >&2")
        assert code == 0
        assert "err" in err

    async def test_nonzero_exit(self):
        code, out, err = await bash("exit 42")
        assert code == 42
