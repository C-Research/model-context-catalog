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


def _reject_unsafe_members(names: list[str], dest: Path) -> None:
    """Raise if any archive member would extract outside dest (zip slip).

    zipfile.extractall has no equivalent of tarfile's `filter="data"` (added in
    3.12), so a malicious entry name like '../../etc/passwd' or an absolute
    path is not rejected by the stdlib and must be checked here before
    extraction.
    """
    for name in names:
        target = (dest / name).resolve()
        if not target.is_relative_to(dest):
            raise ValueError(f"Archive member escapes destination: {name!r}")


def extract(path: str, dest: str) -> list[str]:
    """Extract a zip or tar archive to a destination directory. Returns extracted paths."""
    dest_path = Path(dest)
    dest_path.mkdir(parents=True, exist_ok=True)
    dest_path = dest_path.resolve()
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
            _reject_unsafe_members(names, dest_path)
            zf.extractall(dest_path)  # nosec B202 -- members validated above
            return names
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
