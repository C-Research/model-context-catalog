import tarfile
import zipfile
from pathlib import Path


def list_archive(path: str) -> list[str]:
    """List the contents of a zip or tar archive."""
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as zf:
            return zf.namelist()
    if tarfile.is_tarfile(path):
        with tarfile.open(path) as tf:
            return tf.getnames()
    raise ValueError(f"Unsupported archive format: {path}")


def extract(path: str, dest: str) -> list[str]:
    """Extract a zip or tar archive to a destination directory. Returns extracted paths."""
    dest_path = Path(dest)
    dest_path.mkdir(parents=True, exist_ok=True)
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as zf:
            zf.extractall(dest_path)
            return zf.namelist()
    if tarfile.is_tarfile(path):
        with tarfile.open(path) as tf:
            tf.extractall(dest_path, filter="data")
            return tf.getnames()
    raise ValueError(f"Unsupported archive format: {path}")


def create(dest: str, files: list) -> str:
    """Create a zip or tar.gz archive from a list of file paths. Format is inferred from dest extension."""
    dest_path = Path(dest)
    if dest_path.suffix == ".zip":
        with zipfile.ZipFile(dest_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in files:
                zf.write(f, Path(f).name)
    elif dest_path.name.endswith((".tar.gz", ".tgz")):
        with tarfile.open(dest_path, "w:gz") as tf:
            for f in files:
                tf.add(f, arcname=Path(f).name)
    elif dest_path.name.endswith(".tar"):
        with tarfile.open(dest_path, "w") as tf:
            for f in files:
                tf.add(f, arcname=Path(f).name)
    else:
        raise ValueError(f"Unsupported archive extension: {dest_path.name}")
    return str(dest_path.resolve())
