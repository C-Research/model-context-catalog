import base64
import difflib
import hashlib


def base64_encode(text: str) -> str:
    """Encode text to base64."""
    return base64.b64encode(text.encode()).decode()


def base64_decode(text: str) -> str:
    """Decode a base64-encoded string back to text."""
    return base64.b64decode(text.encode()).decode()


def hash(text: str, algo: str = "sha256") -> str:
    """Hash text using the given algorithm (e.g. sha256, md5, sha1)."""
    h = hashlib.new(algo)
    h.update(text.encode())
    return h.hexdigest()


def diff(a: str, b: str) -> str:
    """Produce a unified diff between two strings."""
    return "\n".join(
        difflib.unified_diff(
            a.splitlines(keepends=True),
            b.splitlines(keepends=True),
            fromfile="a",
            tofile="b",
        )
    )
