import os
import platform
import sys


def get_env(keys: list) -> dict:
    """Get one or more environment variables. Returns a dict of key to value (or None if unset)."""
    return {k: os.environ.get(k) for k in keys}


def set_env(key: str, value: str) -> None:
    """Set an environment variable."""
    os.environ[key] = value


def list_env() -> list[str]:
    """Return all environment variable names."""
    return sorted(os.environ.keys())


def info() -> dict:
    """Return OS, Python version, CPU architecture, and hostname."""
    return {
        "os": platform.system(),
        "os_version": platform.version(),
        "arch": platform.machine(),
        "python": platform.python_version(),
        "hostname": platform.node(),
        "cpus": os.cpu_count(),
    }


def path() -> list[str]:
    """Return the current Python sys.path."""
    return sys.path.copy()
