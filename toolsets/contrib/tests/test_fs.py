import pytest

from toolsets.contrib.fs import list_dir, move, read_file, stat, write_file


class TestReadFile:
    async def test_reads_text(self, tmp_path):
        f = tmp_path / "hello.txt"
        f.write_text("hello world")
        result = await read_file(str(f))
        assert result == "hello world"

    async def test_reads_binary(self, tmp_path):
        f = tmp_path / "data.bin"
        f.write_bytes(b"\x00\x01\x02")
        result = await read_file(str(f), mode="rb")
        assert result == b"\x00\x01\x02"

    async def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            await read_file(str(tmp_path / "nope.txt"))


class TestWriteFile:
    async def test_writes_text(self, tmp_path):
        f = tmp_path / "out.txt"
        await write_file(str(f), "content")
        assert f.read_text() == "content"

    async def test_writes_bytes(self, tmp_path):
        f = tmp_path / "out.bin"
        await write_file(str(f), b"content", mode="wb")
        assert f.read_bytes() == b"content"

    async def test_creates_parent_dirs(self, tmp_path):
        f = tmp_path / "a" / "b" / "out.txt"
        await write_file(str(f), "nested")
        assert f.read_text() == "nested"

    async def test_append_mode(self, tmp_path):
        f = tmp_path / "log.txt"
        await write_file(str(f), "first")
        await write_file(str(f), " second", mode="a")
        assert f.read_text() == "first second"


class TestListDir:
    async def test_lists_entries(self, tmp_path):
        (tmp_path / "a.txt").touch()
        (tmp_path / "b.txt").touch()
        result = await list_dir(str(tmp_path))
        names = [p.name for p in result]
        assert sorted(names) == ["a.txt", "b.txt"]

    async def test_glob_pattern(self, tmp_path):
        (tmp_path / "a.txt").touch()
        (tmp_path / "b.py").touch()
        result = await list_dir(str(tmp_path), pattern="*.py")
        assert len(result) == 1
        assert result[0].name == "b.py"

    async def test_recursive(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "deep.txt").touch()
        result = await list_dir(str(tmp_path), pattern="*.txt", recursive=True)
        assert any(p.name == "deep.txt" for p in result)

    async def test_not_a_dir_raises(self, tmp_path):
        f = tmp_path / "file.txt"
        f.touch()
        with pytest.raises(ValueError, match="not found"):
            await list_dir(str(f))


class TestMove:
    def test_renames_file(self, tmp_path):
        src = tmp_path / "old.txt"
        src.write_text("data")
        dst = tmp_path / "new.txt"
        result = move(str(src), str(dst))
        assert not src.exists()
        assert dst.read_text() == "data"
        assert result == str(dst)

    def test_missing_source_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            move(str(tmp_path / "ghost"), str(tmp_path / "dst"))


class TestStat:
    def test_existing_file(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("hi")
        result = stat(str(f))
        assert result["exists"] is True
        assert result["is_file"] is True
        assert result["is_dir"] is False
        assert result["size"] == 2
        assert "mtime" in result

    def test_existing_dir(self, tmp_path):
        result = stat(str(tmp_path))
        assert result["exists"] is True
        assert result["is_dir"] is True
        assert result["is_file"] is False

    def test_missing_path(self, tmp_path):
        result = stat(str(tmp_path / "nope"))
        assert result["exists"] is False
