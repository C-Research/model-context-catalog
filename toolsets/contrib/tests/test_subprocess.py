from toolsets.contrib.subprocess import bash


class TestBash:
    async def test_captures_stdout(self):
        out = await bash("echo hello")
        assert out.strip() == "hello"

    async def test_nonzero_exit(self):
        code, out, err = await bash("exit 42")
        assert code == 42
