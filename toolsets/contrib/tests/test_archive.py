import tarfile
import zipfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mcc.app import execute

_CTX = MagicMock()


@pytest.fixture(autouse=True)
async def _load(load_contrib):
    load_contrib("archive.yaml")


def _make_files(tmp_path, names=("a.txt", "b.txt")):
    tmp_path.mkdir(parents=True, exist_ok=True)
    paths = []
    for name in names:
        f = tmp_path / name
        f.write_text(f"content of {name}")
        paths.append(str(f))
    return paths


class TestCreateAndList:
    async def test_create_zip(self, tmp_path):
        files = _make_files(tmp_path)
        dest = str(tmp_path / "out.zip")
        result = await execute(_CTX, "admin.archive.create", {"dest": dest, "files": files})
        assert Path(result).exists()
        assert zipfile.is_zipfile(result)

    async def test_create_tar_gz(self, tmp_path):
        files = _make_files(tmp_path)
        dest = str(tmp_path / "out.tar.gz")
        result = await execute(_CTX, "admin.archive.create", {"dest": dest, "files": files})
        assert Path(result).exists()
        assert tarfile.is_tarfile(result)

    async def test_create_tar(self, tmp_path):
        files = _make_files(tmp_path)
        dest = str(tmp_path / "out.tar")
        result = await execute(_CTX, "admin.archive.create", {"dest": dest, "files": files})
        assert Path(result).exists()

    async def test_list_zip(self, tmp_path):
        files = _make_files(tmp_path)
        dest = str(tmp_path / "out.zip")
        await execute(_CTX, "admin.archive.create", {"dest": dest, "files": files})
        result = await execute(_CTX, "admin.archive.list", {"path": dest})
        assert sorted(result) == ["a.txt", "b.txt"]

    async def test_list_tar_gz(self, tmp_path):
        files = _make_files(tmp_path)
        dest = str(tmp_path / "out.tar.gz")
        await execute(_CTX, "admin.archive.create", {"dest": dest, "files": files})
        result = await execute(_CTX, "admin.archive.list", {"path": dest})
        assert sorted(result) == ["a.txt", "b.txt"]

    async def test_unsupported_format(self, tmp_path):
        f = tmp_path / "not_an_archive.txt"
        f.write_text("hello")
        # fn tools run in a subprocess; errors come back as (code, stdout, stderr)
        result = await execute(_CTX, "admin.archive.list", {"path": str(f)})
        code, _, stderr = result
        assert code != 0
        assert "Unsupported" in stderr


class TestExtract:
    async def test_extract_zip(self, tmp_path):
        files = _make_files(tmp_path / "src")
        archive = str(tmp_path / "out.zip")
        await execute(_CTX, "admin.archive.create", {"dest": archive, "files": files})
        dest = str(tmp_path / "extracted")
        result = await execute(_CTX, "admin.archive.extract", {"path": archive, "dest": dest})
        assert sorted(result) == ["a.txt", "b.txt"]
        assert (Path(dest) / "a.txt").read_text() == "content of a.txt"

    async def test_extract_tar_gz(self, tmp_path):
        files = _make_files(tmp_path / "src")
        archive = str(tmp_path / "out.tar.gz")
        await execute(_CTX, "admin.archive.create", {"dest": archive, "files": files})
        dest = str(tmp_path / "extracted")
        result = await execute(_CTX, "admin.archive.extract", {"path": archive, "dest": dest})
        assert sorted(result) == ["a.txt", "b.txt"]
        assert (Path(dest) / "b.txt").read_text() == "content of b.txt"

    async def test_creates_dest_dir(self, tmp_path):
        files = _make_files(tmp_path / "src")
        archive = str(tmp_path / "out.zip")
        await execute(_CTX, "admin.archive.create", {"dest": archive, "files": files})
        dest = str(tmp_path / "deep" / "nested" / "out")
        await execute(_CTX, "admin.archive.extract", {"path": archive, "dest": dest})
        assert (Path(dest) / "a.txt").exists()
