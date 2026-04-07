import asyncio
import json
import os
import shlex
import sys
from pathlib import Path
from time import time
from typing import Any, Callable

from jinja2 import Environment, StrictUndefined
from dotenv import dotenv_values

from mcc.settings import logger


def _quote_filter(value: Any) -> str:
    if isinstance(value, list):
        return " ".join(shlex.quote(str(v)) for v in value)
    return shlex.quote(str(value))


_jinja_env = Environment(undefined=StrictUndefined)
_jinja_env.filters["quote"] = _quote_filter


_LIMIT_SIGNALS = {
    -24: "cpu time exceeded (SIGXCPU)",
    -25: "file size exceeded (SIGXFSZ)",
    -9: "killed (SIGKILL)",
}


def _build_env(
    env: dict[str, str] | None,
    env_file: str | None,
    env_passthrough: bool = False,
) -> dict[str, str] | None:
    """Build the subprocess environment.

    When env_passthrough is False (default) the base is an empty dict, so the
    subprocess only receives variables explicitly declared via env/env_file.
    When env_passthrough is True the base is a copy of os.environ, and
    env_file/env are overlaid on top (original behaviour).

    Returns None when no configuration is provided and env_passthrough is False,
    which lets the subprocess inherit the parent environment through the OS
    default (identical to the unconfigured case).
    """
    if not env and not env_file and not env_passthrough:
        return None

    merged = dict(os.environ) if env_passthrough else {}
    if env_file:
        merged.update(
            {k: v for k, v in dotenv_values(env_file).items() if v is not None}
        )
    if env:
        merged.update(env)
    return merged


def _build_preexec_fn(limits: dict) -> Callable | None:
    """Build a preexec_fn that sets resource limits. Unix only."""
    if sys.platform == "win32" or not limits:
        return
    import resource

    limit_map = {
        "mem_mb": ("RLIMIT_AS", lambda v: v * 1024 * 1024),
        "cpu_sec": ("RLIMIT_CPU", lambda v: v),
        "fsize_mb": ("RLIMIT_FSIZE", lambda v: v * 1024 * 1024),
        "nofile": ("RLIMIT_NOFILE", lambda v: v),
    }

    def _apply():
        for key, (attr, convert) in limit_map.items():
            if key not in limits:
                continue
            rlimit = getattr(resource, attr, None)
            if rlimit is None:
                continue
            val = convert(limits[key])
            try:
                resource.setrlimit(rlimit, (val, val))
            except (ValueError, OSError):
                pass

    return _apply


async def _communicate_and_return(
    proc: asyncio.subprocess.Process,
    blob: bytes | None,
    timeout: int | None,
    limits: dict | None,
) -> str | tuple[int, str, str]:
    """Communicate with a subprocess and return the standard MCC result envelope.

    Returns stdout string on success (exit code 0), or (code, stdout, stderr) on
    failure. Handles timeout and resource-limit signal mapping.
    """
    t0 = time()
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(blob), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return (-1, "", f"timeout after {timeout}s")

    elapsed_ms = int((time() - t0) * 1000)
    code = proc.returncode or 0
    out = stdout.decode()
    if code == 0:
        logger.debug("subprocess finished in %dms", elapsed_ms)
        return out
    err = stderr.decode()

    if code < 0 and limits:
        reason = _LIMIT_SIGNALS.get(code, f"signal {-code}")
        err = f"resource limit hit: {reason} [limits: {limits}]\n{err}"

    return (code, out, err)


def make_exec_callable(
    cmd: str,
    use_stdin: bool,
    timeout: int | None,
    limits: dict | None,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    env_file: str | None = None,
    env_passthrough: bool = False,
) -> Callable:
    """Generate an async closure that runs cmd as a subprocess."""
    preexec_fn = _build_preexec_fn(limits or {})
    merged_env = _build_env(env, env_file, env_passthrough)

    template = _jinja_env.from_string(cmd)

    async def _exec(**kwargs: Any) -> str | tuple[int, str, str]:
        run_cmd = template.render(**kwargs)
        logger.debug("exec: %s | %s", json.dumps(kwargs), run_cmd)
        stdin_pipe = asyncio.subprocess.PIPE if use_stdin else None

        extra: dict[str, Any] = {}
        if preexec_fn is not None:
            extra["preexec_fn"] = preexec_fn
        if cwd is not None:
            extra["cwd"] = cwd
        if merged_env is not None:
            extra["env"] = merged_env

        proc = await asyncio.create_subprocess_shell(
            run_cmd,
            stdin=stdin_pipe,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            **extra,
        )

        blob = json.dumps(kwargs).encode() if use_stdin else None
        return await _communicate_and_return(proc, blob, timeout, limits)

    return _exec


def make_py_callable(
    fn_path: str,
    python: str,
    timeout: int | None,
    limits: dict | None,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    env_file: str | None = None,
    env_passthrough: bool = False,
) -> Callable:
    """Generate an async closure that runs fn_path in a separate Python interpreter."""
    pyrunner_path = str(Path(__file__).with_name("pyrunner.py"))
    preexec_fn = _build_preexec_fn(limits or {})
    merged_env = _build_env(env, env_file, env_passthrough)

    async def _exec(**kwargs: Any) -> str | tuple[int, str, str]:
        logger.debug("py_exec: %s | %s %s", json.dumps(kwargs), python, fn_path)

        extra: dict[str, Any] = {}
        if preexec_fn is not None:
            extra["preexec_fn"] = preexec_fn
        if cwd is not None:
            extra["cwd"] = cwd
        if merged_env is not None:
            extra["env"] = merged_env

        proc = await asyncio.create_subprocess_exec(
            python,
            pyrunner_path,
            "exec",
            fn_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            **extra,
        )

        blob = json.dumps(kwargs).encode()
        return await _communicate_and_return(proc, blob, timeout, limits)

    return _exec
