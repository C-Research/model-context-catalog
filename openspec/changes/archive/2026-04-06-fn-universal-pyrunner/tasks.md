## 1. pyrunner.py

- [x] 1.1 Update `introspect` to accept N fn_paths from `sys.argv[2:]`
- [x] 1.2 Phase 1 — resolve all fn_paths first: for each fn_path call `resolve()` in a try/except; record successes and failures separately; failures get `{"fn_path": ..., "error": traceback.format_exc()}`
- [x] 1.3 Phase 2 — inspect only successfully resolved fns: for each, call `inspect.signature`, `inspect.getdoc`, extract return annotation; wrap in try/except; failures get same error shape
- [x] 1.4 Add `return_type` to each success entry: `str(hint)` if annotated, `None` if `inspect.Parameter.empty`
- [x] 1.5 Emit combined results as a JSON array to stdout; process exits 0 regardless of per-item errors so the caller can distinguish item failures from a subprocess crash
- [x] 1.4 Print final JSON array to stdout (replaces the current single-object print)

## 2. models.py

- [x] 2.1 In `validate_fn_or_exec`: when `fn` is set and `python` is `None`, set `self.python = sys.executable`; `python` is now always non-None for fn tools after validation
- [x] 2.2 Add `return_type: str | None = None` field to `ToolModel`
- [x] 2.3 In `introspect` validator: call `subprocess.run(python, pyrunner, "introspect", fn)`, parse `result[0]` from the JSON array; on per-item `error` key raise `ValueError` with the full traceback text so Pydantic surfaces it with the fn path in context
- [x] 2.4 In `callable` cached_property: remove the `if self.python` branch and `return resolve(self.fn)` fallback — always call `make_py_callable`
- [x] 2.5 In `signature` property: replace `inspect.signature(self.callable).return_annotation` lookup with `self.return_type or "unknown"`
- [x] 2.6 Remove `params_from_signature()` function and `from mcc.pyrunner import resolve` import; remove `import inspect` if no longer used elsewhere; clean up any now-dead branches

## 3. loader.py

- [x] 3.1 Add `_batch_introspect(python: str, entries: list[dict]) -> dict[str, dict]` — runs one subprocess for all fn_paths in `entries`, returns a map of `fn_path → introspect result`; raises on subprocess failure; surfaces per-item errors as `ValueError`
- [x] 3.2 In `load_file`: after parsing YAML, separate fn entries that need introspection (have `fn` set, no explicit `params`) from others; resolve each entry's python (default `sys.executable`); group by python path
- [x] 3.3 For each interpreter group, call `_batch_introspect`; on per-item error, raise `ValueError` with a message in the form `"Failed to load tool '{fn_path}' from {yaml_path}:\n{traceback}"` — exact fn path and source file both present
- [x] 3.4 Inject `name`, `description`, `params`, `return_type` into the raw entry dict before `ToolModel` construction; validator sees `params` already populated and skips the per-tool subprocess

## 4. Tests

- [x] 4.1 `test_pyrunner.py`: update introspect tests — invocation now passes multiple fn_paths; stdout is a JSON array; verify `return_type` is present and correct for annotated and unannotated functions
- [x] 4.2 `test_pyrunner.py`: test batch introspect with a mix of valid and invalid fn_paths — valid entries succeed, invalid emit `error` key containing a traceback string, process exits 0; verify errors for: missing module (phase 1), missing attribute (phase 1), callable that raises during `inspect.signature()` (phase 2); verify that a phase-1 failure does not prevent phase-2 inspection of other fns
- [x] 4.3 `test_loader.py`: verify that loading a file with multiple fn tools sharing the same interpreter triggers exactly one introspect subprocess (mock/spy `subprocess.run`)
- [x] 4.4 `test_loader.py`: verify that fn entries with explicit `params` skip the batch pre-pass entirely
- [x] 4.5 `test_exec.py`: verify fn tools constructed directly (not via loader) still work — `ToolModel(fn=..., python=sys.executable)` introspects and calls correctly
- [x] 4.6 `test_exec.py`: verify fn tools with no `python` field behave identically to those with `python: sys.executable`
- [x] 4.7 `test_loader.py`: verify contrib tools load correctly through the subprocess path (use a contrib fn that is importable in the test env)
