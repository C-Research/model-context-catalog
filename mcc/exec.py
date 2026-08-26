import asyncio
import json
import os
import sys
from collections.abc import Callable
from fnmatch import fnmatchcase
from pathlib import Path
from time import time
from typing import Any

from dotenv import dotenv_values

from mcc.context import (
    assemble_context,
    ctx_blob_env,
    ctx_expanded_env,
    current_context_var,
    current_user_var,
    writeback_context_var,
)
from mcc.settings import logger, settings
from mcc.template import jinja_env

_LIMIT_SIGNALS = {
    -24: "cpu time exceeded (SIGXCPU)",
    -25: "file size exceeded (SIGXFSZ)",
    -9: "killed (SIGKILL)",
}


def _build_env(
    env: dict[str, str] | None,
    env_file: str | None,
    env_passthrough: bool | list[str] = False,
) -> dict[str, str]:
    """Build the subprocess environment.

    The base always starts from the configurable env floor (settings.ENV_FLOOR):
    a fixed set of "machine works" variables (PATH, HOME, ...) that are exposed
    regardless of env_passthrough, including when it is False. A floor name is
    only included if present in os.environ.

    env_passthrough then widens the base:
      - False (default): floor only.
      - list[str]: each entry is an fnmatchcase (case-sensitive) glob matched
        against os.environ keys; matching variables are merged over the floor.
      - True: the entire parent environment (the floor is a subset).

    env_file is overlaid next, then env (highest precedence). Always returns a
    concrete dict so callers never inherit the full parent environment via an
    OS default or None fallback.
    """
    base = {k: os.environ[k] for k in settings.ENV_FLOOR if k in os.environ}
    if env_passthrough is True:
        base = dict(os.environ)
    elif isinstance(env_passthrough, list):
        base.update(
            {
                k: v
                for k, v in os.environ.items()
                if any(fnmatchcase(k, pat) for pat in env_passthrough)
            }
        )
    if env_file:
        base.update({k: v for k, v in dotenv_values(env_file).items() if v is not None})
    if env:
        base.update(env)
    return base


def _build_pyrunner_env(
    env: dict[str, str] | None,
    env_file: str | None,
    env_passthrough: bool | list[str],
    cwd: str,
) -> dict[str, str]:
    """Build the environment for any pyrunner subprocess (introspect or exec).

    Prepends cwd to PYTHONPATH so tool fn modules are importable, and sets
    MCC_SKIP_AUTOLOAD to prevent recursive loader spawning on import.
    """
    result = dict(_build_env(env, env_file, env_passthrough))
    result["MCC_SKIP_AUTOLOAD"] = "1"
    existing = result.get("PYTHONPATH", "")
    result["PYTHONPATH"] = f"{cwd}{os.pathsep}{existing}" if existing else cwd
    return result


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
    except TimeoutError:
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


async def _apply_transform(
    data: str,
    cmd: str,
    timeout: int | None,
) -> str | tuple[int, str, str]:
    """Pipe data through a shell command and return the result."""
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    return await _communicate_and_return(proc, data.encode(), timeout, limits=None)


def _context_env(kind: str) -> dict[str, str]:
    """Build the context env vars for this spawn from the request-scoped context.

    fn tools get the whole dict as one JSON blob (MCC_CTX); exec tools get each
    entry expanded into MCC_CTX_<NAME>. The context is assembled fresh from
    current_user_var so identity always reflects the caller of *this* invocation
    (identity wins over any stored value). Anonymous requests still carry
    user="anonymous".
    """
    context = current_context_var.get(None)
    if context is None:
        # No execute() snapshot (e.g. direct callable use); derive identity only.
        context = assemble_context(None, current_user_var.get(None))
    return ctx_blob_env(context) if kind == "fn" else ctx_expanded_env(context)


def _proc_extra(
    preexec_fn: Callable | None,
    cwd: str | None,
    base_env: dict[str, str] | None,
    kind: str,
) -> dict[str, Any]:
    """Assemble create_subprocess_* kwargs, merging the caller's context into env
    last (highest precedence, so a tool's own env cannot spoof identity).

    Call this per spawn, not at build time: it reads the request-scoped context
    so the env reflects the caller of *this* invocation. The expensive pieces
    (preexec_fn, base_env) are built once and passed in. ``kind`` selects the
    propagation shape: "fn" → MCC_CTX blob, "exec" → MCC_CTX_<NAME> expansion.
    """
    extra: dict[str, Any] = {}
    if preexec_fn is not None:
        extra["preexec_fn"] = preexec_fn
    if cwd is not None:
        extra["cwd"] = cwd
    ctx_env = _context_env(kind)
    if base_env is not None or ctx_env:
        extra["env"] = {**(base_env or {}), **ctx_env}
    return extra


def _sanitize_fn_traceback(err: str) -> str:
    """Reduce a pyrunner-emitted Python traceback to its final exception message.

    pyrunner prints the full traceback (source file paths, line numbers, code
    context) to stderr on an uncaught exception. Unless settings.DEBUG is on,
    that would leak the tool's source code to the LLM, so only the exception's
    type and message survive. The message itself can span multiple lines (e.g.
    a pydantic ValidationError's field-by-field breakdown), so this finds the
    last "  File ..." frame header and returns everything from the first line
    after it that isn't more indented than that header — frame source snippets
    and caret annotations are always indented deeper than their "File" line,
    while the exception repr that follows can dedent back to column 0. Non-
    traceback stderr (timeouts, resource-limit notices) is left untouched.
    """
    if settings.get("DEBUG", False) or "Traceback (most recent call last):" not in err:
        return err
    lines = [line for line in err.strip().splitlines() if line.strip()]
    last_file = next(
        (i for i in range(len(lines) - 1, -1, -1) if lines[i].lstrip().startswith('File "')),
        None,
    )
    if last_file is None:
        return lines[-1] if lines else err
    file_indent = len(lines[last_file]) - len(lines[last_file].lstrip())
    start = last_file + 1
    while start < len(lines) and (len(lines[start]) - len(lines[start].lstrip())) > file_indent:
        start += 1
    return "\n".join(lines[start:]) if start < len(lines) else lines[-1]


def _unwrap_fn_envelope(raw: str) -> str:
    """Unwrap pyrunner's [result, context] stdout envelope for an fn tool.

    Returns the JSON-encoded result (element 0) and stashes the returned context
    (element 1) on writeback_context_var for app.execute to write back. Tolerant of
    a malformed payload (like _load_context): if `raw` is not a 2-element JSON array,
    it is passed through unchanged and no write-back is recorded.
    """
    try:
        envelope = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return raw
    if not (isinstance(envelope, list) and len(envelope) == 2):
        return raw
    result, context = envelope
    if context is not None:
        writeback_context_var.set(context)
    return json.dumps(result)


def _make_callable(
    limits: dict | None,
    transform: str | None,
    create_proc: Callable,
    is_fn: bool = False,
) -> Callable:
    """Wrap a proc-spawning coroutine into an MCC tool callable.

    fn tools (is_fn=True) emit pyrunner's [result, context] envelope on stdout: it is
    unwrapped to the bare result before transform/return, and the returned context is
    stashed for write-back. exec tools emit their result directly (read-only, no
    write-back).
    """
    timeout = limits.get("timeout") if limits else None
    transform_template = jinja_env.from_string(transform) if transform else None

    async def _exec(**kwargs: Any) -> str | tuple[int, str, str]:
        proc, blob = await create_proc(**kwargs)
        result = await _communicate_and_return(proc, blob, timeout, limits)
        # Only a success (str) carries the envelope; failure tuples pass through
        # untouched, so no write-back is recorded on error.
        if isinstance(result, str) and is_fn:
            result = _unwrap_fn_envelope(result)
        elif isinstance(result, tuple) and is_fn:
            code, out, err = result
            if err:
                logger.error("py_exec failed: code=%s | %s", code, err)
            result = (code, out, _sanitize_fn_traceback(err))
        if isinstance(result, str) and transform_template:
            result = await _apply_transform(
                result, transform_template.render(**kwargs), timeout
            )
        return result

    return _exec


def make_exec_callable(
    cmd: str,
    use_stdin: bool,
    limits: dict | None,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    env_file: str | None = None,
    env_passthrough: bool | list[str] = False,
    transform: str | None = None,
) -> Callable:
    """Generate an async closure that runs cmd as a subprocess."""
    preexec_fn = _build_preexec_fn(limits or {})
    base_env = _build_env(env, env_file, env_passthrough)
    template = jinja_env.from_string(cmd)

    async def _spawn(**kwargs: Any):
        run_cmd = template.render(**kwargs)
        logger.info("exec: %s | %s", json.dumps(kwargs), run_cmd)
        proc = await asyncio.create_subprocess_shell(
            run_cmd,
            stdin=asyncio.subprocess.PIPE if use_stdin else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            **_proc_extra(preexec_fn, cwd, base_env, "exec"),
        )
        return proc, (json.dumps(kwargs).encode() if use_stdin else None)

    return _make_callable(limits, transform, _spawn)


def make_py_callable(
    fn_path: str,
    python: str,
    limits: dict | None,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    env_file: str | None = None,
    env_passthrough: bool | list[str] = False,
    transform: str | None = None,
) -> Callable:
    """Generate an async closure that runs fn_path in a separate Python interpreter."""
    pyrunner_path = str(Path(__file__).with_name("pyrunner.py"))
    effective_cwd = cwd if cwd else os.getcwd()
    preexec_fn = _build_preexec_fn(limits or {})
    base_env = _build_pyrunner_env(env, env_file, env_passthrough, effective_cwd)

    async def _spawn(**kwargs: Any):
        logger.info("py_exec: %s | %s %s", json.dumps(kwargs), python, fn_path)
        proc = await asyncio.create_subprocess_exec(
            python,
            pyrunner_path,
            "exec",
            fn_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            **_proc_extra(preexec_fn, effective_cwd, base_env, "fn"),
        )
        return proc, json.dumps(kwargs).encode()

    return _make_callable(limits, transform, _spawn, is_fn=True)
