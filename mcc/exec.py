import asyncio
import json
import shlex
import sys
from typing import Any, Callable

from mcc.settings import logger


_LIMIT_SIGNALS = {
    -24: "cpu time exceeded (SIGXCPU)",
    -25: "file size exceeded (SIGXFSZ)",
    -9: "killed (SIGKILL)",
}


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


def make_exec_callable(
    cmd: str, use_stdin: bool, timeout: int | None, limits: dict | None
) -> Callable:
    """Generate an async closure that runs cmd as a subprocess."""
    preexec_fn = _build_preexec_fn(limits or {})

    async def _exec(**kwargs: Any) -> tuple[int, str, str]:
        safe = {k: shlex.quote(str(v)) for k, v in kwargs.items()}
        run_cmd = cmd.format(**safe)
        logger.debug("exec: %s | %s", json.dumps(kwargs), run_cmd)
        stdin_pipe = asyncio.subprocess.PIPE if use_stdin else None

        extra: dict[str, Any] = {}
        if preexec_fn is not None:
            extra["preexec_fn"] = preexec_fn

        proc = await asyncio.create_subprocess_shell(
            run_cmd,
            stdin=stdin_pipe,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            **extra,
        )

        blob = json.dumps(kwargs).encode() if use_stdin else None
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(blob), timeout=timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return (-1, "", f"timeout after {timeout}s")

        code = proc.returncode or 0
        out = stdout.decode()
        err = stderr.decode()

        if code < 0 and limits:
            reason = _LIMIT_SIGNALS.get(code, f"signal {-code}")
            err = f"resource limit hit: {reason} [limits: {limits}]\n{err}"

        return (code, out, err)

    return _exec
