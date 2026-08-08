## 1. pysrc module

- [x] 1.1 Create `toolsets/contrib/pysrc.py` importing `resolve` from `mcc.pyrunner`
- [x] 1.2 Implement `get_docstring(fn_path: str) -> str`
- [x] 1.3 Implement `get_source(fn_path: str) -> str`
- [x] 1.4 Implement `get_signature(fn_path: str) -> dict` (params with name/type/required/default, excluding `*args`/`**kwargs`, plus return_type)
- [x] 1.5 Implement `list_members(module_path: str, kind: str = "all") -> list[dict]`, filtered to members whose `__module__` matches `module_path`
- [x] 1.6 Implement `get_class_hierarchy(fn_path: str) -> dict` (`bases` via MRO, `subclasses` via `__subclasses__()`)
- [x] 1.7 Implement `get_file_location(fn_path: str) -> dict` (`file`, `lineno`, `endlineno`)

## 2. Registration

- [x] 2.1 Create `toolsets/contrib/pysrc.yaml` with `groups: [admin, dev]` and one entry per function, plus an `example:` for each
- [x] 2.2 Add `toolsets/contrib/pysrc.yaml` to `toolsets/contrib/settings.yaml`'s `tools:` list

## 3. Tests

- [x] 3.1 Create `toolsets/contrib/tests/test_pysrc.py` following `test_text.py`'s style (autouse fixture loading `pysrc.yaml` via `load_contrib`, tools invoked through `mcc.app.execute`)
- [x] 3.2 Test each of the six tools against known targets in `mcc.pyrunner`/`mcc.loader` (stable, unlikely to change shape)
- [x] 3.3 Test dotpath error propagation: malformed `fn_path` raises the same error `mcc.pyrunner.resolve` would raise directly

## 4. Verification

- [x] 4.1 Run `uv run pytest toolsets/contrib/tests/test_pysrc.py`
- [x] 4.2 Run `ruff` and `pyright` per `AGENTS.md` across `toolsets/contrib/pysrc.py` and the new test file
