from datetime import datetime
from pathlib import Path

import aiofiles


async def read_file(path: str, mode: str = "r") -> str:
    """
    Read the contents of a file and return as a string.
    """
    async with aiofiles.open(path, mode=mode) as f:
        return await f.read()


async def write_file(path: str, content: str, mode: str = "w") -> None:
    """
    Write content to a file, creating parent directories if needed.
    Use mode=a for appending to files
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(path, mode=mode) as f:
        await f.write(content)


async def list_dir(path: str, pattern: str = "*", recursive=False) -> list[str]:
    """
    List entries in a directory matching a glob pattern.
    Use recursive scan to find entries in any subfolders
    """
    path = Path(path)
    if not path.is_dir():
        raise ValueError(f"Dir {path} not found")
    globber = path.rglob if recursive else path.glob
    return list(globber(pattern))


def move(source: str, destination: str) -> str:
    """
    Move or rename a file or directory.
    Returns the destination path.
    """
    source = Path(source)
    if not source.exists():
        raise FileNotFoundError(f"Path {source} not found")
    return str(source.move(destination))


def stat(path: str) -> dict:
    """
    Return metadata for a path: size, mtime, atime, ctime, is_file, is_dir, exists.
    """
    path = Path(path)
    if not path.exists():
        return {"exists": False, "path": path}
    result = path.stat()
    return {
        "exists": True,
        "path": str(path.resolve()),
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
        "size": result.st_size,
        "mtime": datetime.fromtimestamp(result.st_mtime).isoformat(),
        "atime": datetime.fromtimestamp(result.st_atime).isoformat(),
        "ctime": datetime.fromtimestamp(result.st_ctime).isoformat(),
    }
