from datetime import datetime
from pathlib import Path

import aiofiles


async def read_file(path: str, mode: str = "r") -> str:
    """
    Read the contents of a file and return as a string.
    """
    async with aiofiles.open(path, mode=mode) as f:  # type: ignore[call-overload]  # mode is always a text mode str
        return await f.read()


async def write_file(path: str, content: str, mode: str = "w") -> None:
    """
    Write content to a file, creating parent directories if needed.
    Use mode=a for appending to files
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(path, mode=mode) as f:  # type: ignore[call-overload]  # mode is always a text mode str
        await f.write(content)


async def list_dir(path: str, pattern: str = "*", recursive=False) -> list[Path]:
    """
    List entries in a directory matching a glob pattern.
    Use recursive scan to find entries in any subfolders
    """
    dirpath = Path(path)
    if not dirpath.is_dir():
        raise ValueError(f"Dir {dirpath} not found")
    globber = dirpath.rglob if recursive else dirpath.glob
    return list(globber(pattern))


def move(source: str, destination: str) -> str:
    """
    Move or rename a file or directory.
    Returns the destination path.
    """
    source_path = Path(source)
    if not source_path.exists():
        raise FileNotFoundError(f"Path {source_path} not found")
    return str(source_path.move(destination))


def stat(path: str) -> dict:
    """
    Return metadata for a path: size, mtime, atime, ctime, is_file, is_dir, exists.
    """
    fpath = Path(path)
    if not fpath.exists():
        return {"exists": False, "path": str(fpath)}
    result = fpath.stat()
    return {
        "exists": True,
        "path": str(fpath.resolve()),
        "is_file": fpath.is_file(),
        "is_dir": fpath.is_dir(),
        "size": result.st_size,
        "mtime": datetime.fromtimestamp(result.st_mtime).isoformat(),
        "atime": datetime.fromtimestamp(result.st_atime).isoformat(),
        "ctime": datetime.fromtimestamp(result.st_ctime).isoformat(),
    }
