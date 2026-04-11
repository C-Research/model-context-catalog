## 1. Models

- [x] 1.1 Add `transform: str | list[str] | None = None` field to `ToolModel` in `mcc/models.py`
- [x] 1.2 Add a `_resolved_transform` property or validator that normalizes list to a joined `|` string at load time
- [x] 1.3 Pass `transform` into `make_exec_callable` and `make_py_callable` in `ToolModel.callable`

## 2. Exec tool transform

- [x] 2.1 Add `transform: str | None` parameter to `make_exec_callable` in `mcc/exec.py`
- [x] 2.2 After rendering `run_cmd` from the Jinja template, append `| <transform>` (wrapping original cmd in parens) when transform is set
- [x] 2.3 Render transform string through Jinja with `**kwargs` before appending

## 3. Fn tool transform

- [x] 3.1 Add `_apply_transform(data: str, cmd: str, timeout: int | None) -> str | tuple` helper to `mcc/exec.py`
- [x] 3.2 Helper spawns `subprocess_shell(cmd, stdin=PIPE)`, pipes `data.encode()`, returns result of `_communicate_and_return`
- [x] 3.3 Add `transform: str | None` parameter to `make_py_callable`
- [x] 3.4 In `make_py_callable` closure, after `_communicate_and_return` returns, call `_apply_transform` only when result is `str` and transform is set

## 4. Tests

- [x] 4.1 Add fixture `tests/fixtures/tools_transform.yaml` with exec and fn tools that use `transform`
- [x] 4.2 Test exec tool with string transform (e.g. `head -c 10`)
- [x] 4.3 Test exec tool with list transform joined into pipeline
- [x] 4.4 Test fn tool with transform applied to JSON output
- [x] 4.5 Test that transform is skipped when exec tool exits non-zero
- [x] 4.6 Test that Jinja kwargs are available in the transform expression
