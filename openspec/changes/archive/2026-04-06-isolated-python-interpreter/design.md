## Context

fn-based tools currently execute in-process: `ToolModel.callable` uses `importlib` to import the module and returns a direct reference to the Python callable. This means all fn tools share MCC's interpreter, virtualenv, and sys.path. There is no way to use a tool that requires a different Python version or a conflicting set of dependencies.

`exec` tools already achieve process isolation by spawning a subprocess via `asyncio.create_subprocess_shell`. The new design extends a similar model to fn tools, using a stdlib-only helper script (`pyrunner.py`) that can be run by any Python interpreter.

## Goals / Non-Goals

**Goals:**
- Allow fn tools to specify a `python:` field pointing to an alternative interpreter
- Introspect function signatures through the target interpreter at load time
- Execute fn tools as subprocesses through the target interpreter at call time
- Match the existing exec tool error envelope (`str` on success, `(code, stdout, stderr)` on failure)
- Fail fast at load time if the specified interpreter cannot be found

**Non-Goals:**
- Sandboxing or security isolation (use OS-level tools for that)
- Passing a virtualenv path directly (user points to the venv's Python binary)
- Supporting non-Python runtimes (that's exec tools)
- Changing behavior of fn tools that do not set `python:`

## Decisions

### 1. stdlib-only pyrunner.py

`mcc/pyrunner.py` uses only the Python standard library (`sys`, `json`, `importlib`, `inspect`, `asyncio`). This ensures it can be executed by any Python 3.x interpreter without installing MCC or its dependencies into the target environment.

**Alternative considered**: Generate the runner script inline as a `-c` string argument. Rejected because it's harder to maintain, test, and read.

### 2. Two-mode runner: introspect and exec

`pyrunner.py` supports two invocation modes:

```
python pyrunner.py introspect <fn_path>
# stdout: JSON array of param dicts [{name, type, required, default, description}]

python pyrunner.py exec <fn_path>
# stdin:  JSON kwargs
# stdout: JSON-encoded return value
```

The fn_path format matches ToolModel's existing convention: `module:attr` or `module.attr`.

### 3. Sync subprocess for introspection, async for execution

`model_validator(mode="after")` is synchronous (Pydantic constraint). Introspection uses `subprocess.run` with a short timeout. Execution uses `asyncio.create_subprocess_exec`, matching the exec tool pattern.

**Alternative considered**: Always use async and run introspection via `asyncio.run()` inside the validator. Rejected — `asyncio.run()` fails if an event loop is already running, which is likely in a FastMCP context.

### 4. shutil.which at load time

When `python:` is set, `ToolModel` calls `shutil.which` in the validator to resolve the interpreter path. If the interpreter is not found, a `ValueError` is raised — same failure mode as a bad `fn:` path. This surfaces misconfiguration at `mcc tool add` time, not at first call.

### 5. Error envelope matches exec tools

`make_py_callable` returns `str` on success and `(code, stdout, stderr)` on failure, identical to `make_exec_callable`. Callers need no special casing based on whether a tool uses `python:` or not.

### 6. Return value serialization

pyrunner uses `json.dumps(result, default=str)` on stdout. `default=str` handles common non-serializable types (e.g. `datetime`, `Path`) gracefully. On the MCC side, `make_py_callable` passes stdout through as a string (same as exec tools) — callers that need structured data can `json.loads` it themselves.

### 7. Async function support in pyrunner

pyrunner detects `asyncio.iscoroutinefunction(fn)` and wraps the call in `asyncio.run()`. This handles async fn tools transparently without requiring changes to the tool definition.

## Risks / Trade-offs

**Module must be importable in target env** → The target Python must have the module installed. If it doesn't, introspection fails at load time with a clear ImportError. Mitigation: fail fast with a clear message.

**Subprocess overhead per call** → Each tool call spawns a new process. For high-frequency tools this may be noticeable. Mitigation: this feature is opt-in; performance-sensitive tools should not set `python:`.

**JSON serialization boundary** → kwargs and return values must be JSON-serializable. Types like `bytes`, custom objects, or file handles cannot be passed. Mitigation: `default=str` prevents hard crashes on return; kwargs are already constrained to MCC's TYPE_MAP (`str`, `int`, `float`, `bool`, `list`, `dict`).

**asyncio.run inside pyrunner** → On older Python versions (< 3.7), `asyncio.run` is not available. Mitigation: minimum supported Python is 3.8 across the project; document this constraint.

## Migration Plan

No migration needed. The `python:` field is optional. All existing fn tools without it continue to execute in-process unchanged.
