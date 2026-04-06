## Why

Python fn-based tools currently execute in-process, meaning they share the MCC interpreter, its virtualenv, and its dependencies. This makes it impossible to use tools that require a different Python version or a separate set of installed packages without polluting MCC's own environment.

## What Changes

- Add an optional `python` field to fn-based tool YAML definitions
- At load time, validate the `python` value with `shutil.which` and fail early if not found
- When `python` is set, introspect the function signature by spawning a subprocess at load time (sync) rather than importing in-process
- When `python` is set, execute the tool by spawning a subprocess at call time (async) rather than calling in-process
- Add `mcc/pyrunner.py` — a stdlib-only helper script that handles both introspection and execution, runnable by any Python interpreter
- Add `make_py_callable` to `mcc/exec.py` following the same signature and error envelope as `make_exec_callable`

## Capabilities

### New Capabilities

- `isolated-python-tool`: Run a fn-based tool in a separate Python interpreter, with subprocess-based introspection and execution via a stdlib-only runner script

### Modified Capabilities

- `exec-tool`: `make_py_callable` added alongside existing `make_exec_callable`; same error envelope contract (`str` on success, `(code, stdout, stderr)` on failure)

## Impact

- `mcc/models.py`: new `python` field on `ToolModel`; conditional introspection and callable resolution paths
- `mcc/exec.py`: new `make_py_callable` function
- `mcc/pyrunner.py`: new stdlib-only file
- Tool YAML format: new optional `python:` key on fn tools
- No breaking changes to existing tools; `python` field is opt-in
