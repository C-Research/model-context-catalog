## Why

All fn-based tools now have a subprocess execution path (via `pyrunner.py`) from the `isolated-python-interpreter` change. The in-process path — direct `resolve()` + `params_from_signature()` — is redundant and creates two diverging code paths with different capabilities. The subprocess path is strictly more capable: it supports isolated interpreters, cwd, env, env_file, and works identically regardless of the tool's target Python.

Making pyrunner the universal path for all fn tools simplifies the model significantly. `python` defaults to `sys.executable` so existing tools require no changes.

A secondary problem: each fn tool currently spawns one introspect subprocess at load time. With many tools sharing the same interpreter, this is N processes where one would do. Batch introspection amortizes the cost.

## What Changes

- `python` on fn-based tools defaults to `sys.executable` — always uses the subprocess path
- Drop the in-process fn execution path (`resolve()` import in models.py, `params_from_signature()`)
- `pyrunner.py introspect` accepts multiple fn_paths and returns a JSON array with per-item results including `return_type`; each failure entry includes the full traceback so the caller knows exactly what went wrong
- Loader pre-pass: groups fn tools by python interpreter, batch-introspects each interpreter group in one subprocess call, injects results before `ToolModel` construction
- Load-time failures are reported with the tool's fn path, the source YAML file, and the full stderr from the introspect subprocess — making misconfigured tools immediately actionable
- `ToolModel` gains a `return_type` field; `signature` property uses it instead of `inspect.signature(self.callable)`

## Capabilities

### Modified Capabilities

- `fn-tool`: now always executes via pyrunner subprocess; `python` defaults to `sys.executable`; no behavior change for tools without an explicit `python:` field
- `isolated-python-tool`: `python` field is no longer opt-in gating — it exists on all fn tools

### Removed Capabilities

- In-process fn execution (no `python` field): replaced universally by subprocess execution via `sys.executable`

## Impact

- `mcc/pyrunner.py`: `introspect` accepts N fn_paths via argv, returns JSON array, adds `return_type` per entry
- `mcc/models.py`: `python` defaults to `sys.executable`; drop `params_from_signature`, `resolve` import, in-process branches; add `return_type` field
- `mcc/loader.py`: pre-pass batches introspection by interpreter before constructing `ToolModel`
- No breaking changes to tool YAML format; `python:` remains optional
