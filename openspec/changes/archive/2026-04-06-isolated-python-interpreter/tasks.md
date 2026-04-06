## 1. pyrunner.py

- [x] 1.1 Create `mcc/pyrunner.py` with `resolve(fn_path)` that handles both `module:attr` and `module.attr` formats; refactor the equivalent logic out of `ToolModel.callable` in `mcc/models.py` and replace it with an import of `resolve` from `pyrunner`
- [x] 1.2 Implement `introspect(fn_path)` mode: inspect signature, output JSON array of param dicts `[{name, type, required, default, description}]`
- [x] 1.3 Implement `exec(fn_path)` mode: read JSON kwargs from stdin, call function, print `json.dumps(result, default=str)` to stdout
- [x] 1.4 Add async fn support in exec mode: detect `asyncio.iscoroutinefunction` and wrap in `asyncio.run()`
- [x] 1.5 Ensure pyrunner uses only stdlib imports

## 2. exec.py

- [x] 2.1 Extract `_communicate_and_return(proc, blob, timeout, limits)` private async helper from `make_exec_callable` — handles wait_for, timeout kill, decode, signal mapping, and return envelope
- [x] 2.2 Refactor `make_exec_callable` to use `_communicate_and_return`
- [x] 2.3 Add `make_py_callable(fn_path, python, timeout, limits)` — spawns `asyncio.create_subprocess_exec(python, pyrunner_path, "exec", fn_path)` with stdin=PIPE, applies `_build_preexec_fn(limits)`, sends JSON kwargs on stdin, delegates to `_communicate_and_return`

## 3. models.py

- [x] 3.1 Add `python: str | None = None` field to `ToolModel`
- [x] 3.2 Add validator: when `python` is set, resolve with `shutil.which` and raise `ValueError` if not found
- [x] 3.3 Add validator: raise `ValueError` if `python` is set alongside `exec`
- [x] 3.4 In `introspect` validator: when `python` is set and `params` not declared, spawn `subprocess.run(python, pyrunner, "introspect", fn)` and parse stdout to populate `self.params`
- [x] 3.5 In `callable` cached_property: when `python` is set, return `make_py_callable(self.fn, python_path, self.timeout, self.limits)` instead of direct import

## 4. Tests

- [x] 4.1 Add fixture fns to `tests/example.py`: `add(x: int, y: int) -> int`, `async_add(x: int, y: int) -> int`, `always_fails(msg: str) -> str`
- [x] 4.2 `test_pyrunner.py`: test `resolve()` directly for `module:attr`, `module.attr`, chained traversal, and nonexistent module
- [x] 4.3 `test_pyrunner.py`: test pyrunner as subprocess — introspect mode returns correct JSON schema
- [x] 4.4 `test_pyrunner.py`: test pyrunner as subprocess — exec mode returns JSON result; async fn handled via asyncio.run; unhandled exception gives nonzero exit + stderr
- [x] 4.5 `test_exec.py`: `TestPyCallable` — `make_py_callable` returns str on success, `(code, stdout, stderr)` on failure, `(-1, "", "timeout after Ns")` on timeout
- [x] 4.6 `test_loader.py`: `TestIsolatedPython` — params auto-populated via introspection; explicit params skip introspection; unknown interpreter raises `ValueError`; `python + exec` raises `ValueError`; full `call()` round-trip; async fn end-to-end
