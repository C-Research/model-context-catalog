## 1. Models

- [ ] 1.1 Add `transform: str | list[str] | None = None` field to `ToolModel` in `mcc/models.py`
- [ ] 1.2 Add a `_resolved_transform` property or validator that normalizes list to a joined `|` string at load time
- [ ] 1.3 Pass `transform` into `make_exec_callable` and `make_py_callable` in `ToolModel.callable`

## 2. Exec tool transform

- [ ] 2.1 Add `transform: str | None` parameter to `make_exec_callable` in `mcc/exec.py`
- [ ] 2.2 After rendering `run_cmd` from the Jinja template, append `| <transform>` (wrapping original cmd in parens) when transform is set
- [ ] 2.3 Render transform string through Jinja with `**kwargs` before appending

## 3. Fn tool transform

- [ ] 3.1 Add `_apply_transform(data: str, cmd: str, timeout: int | None) -> str | tuple` helper to `mcc/exec.py`
- [ ] 3.2 Helper spawns `subprocess_shell(cmd, stdin=PIPE)`, pipes `data.encode()`, returns result of `_communicate_and_return`
- [ ] 3.3 Add `transform: str | None` parameter to `make_py_callable`
- [ ] 3.4 In `make_py_callable` closure, after `_communicate_and_return` returns, call `_apply_transform` only when result is `str` and transform is set

## 4. Tests

- [ ] 4.1 Add fixture `tests/fixtures/tools_transform.yaml` with exec and fn tools that use `transform`
- [ ] 4.2 Test exec tool with string transform (e.g. `head -c 10`)
- [ ] 4.3 Test exec tool with list transform joined into pipeline
- [ ] 4.4 Test fn tool with transform applied to JSON output
- [ ] 4.5 Test that transform is skipped when exec tool exits non-zero
- [ ] 4.6 Test that Jinja kwargs are available in the transform expression
