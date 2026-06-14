## 1. Settings

- [x] 1.1 Add `env_floor:` list under `default:` in `mcc/settings.yaml` with `PATH, HOME, USER, LOGNAME, TMPDIR, LANG, LC_ALL, TZ, TERM, SHELL`
- [x] 1.2 Confirm `settings.ENV_FLOOR` resolves (dynaconf uppercase access) and is overridable via `MCC_ENV_FLOOR` / `settings.local.yaml`

## 2. models.py

- [x] 2.1 Change `env_passthrough: bool = False` to `env_passthrough: bool | list[str] = False`
- [x] 2.2 In the `introspect` validator, pass `self.env_passthrough` (not hardcoded `False`) to `_build_pyrunner_env`

## 3. exec.py

- [x] 3.1 Import `fnmatchcase` from `fnmatch` and `settings` from `mcc.settings` (logger import already present — extend it) at module level
- [x] 3.2 Rewrite `_build_env`: floor-first base from `settings.ENV_FLOOR` (only keys present in `os.environ`); `env_passthrough is True` → `dict(os.environ)`; `isinstance(list)` → merge `fnmatchcase` matches over floor; `False` → floor only; then overlay `env_file`, then `env`; **always return a concrete dict**
- [x] 3.3 Delete the early `if not env and not env_file and not env_passthrough: return None` guard and update the docstring (no more `None` return)
- [x] 3.4 Simplify `_build_pyrunner_env`: `result = dict(base)` (base is never `None` now), drop the `os.environ` fallback; keep `MCC_SKIP_AUTOLOAD` and `PYTHONPATH=cwd` injection
- [x] 3.5 Update type annotations on `_build_env`, `_build_pyrunner_env`, `make_exec_callable`, `make_py_callable`: `env_passthrough: bool` → `bool | list[str]`

## 4. Tests (test_exec.py)

- [x] 4.1 List allowlist: `env_passthrough: ["AWS_*", "HOME"]` includes matching parent vars, excludes non-matching (e.g. `GITHUB_TOKEN`)
- [x] 4.2 Case sensitivity: `["PATH"]` matches `PATH`, `["path"]` does not (use `monkeypatch.setenv`)
- [x] 4.3 Empty list behaves like `false` (floor only)
- [x] 4.4 Floor present under `env_passthrough: false`; a parent secret (`MCC_TEST_SECRET`) is absent
- [x] 4.5 Floor variable absent from parent is not set to empty in the subprocess
- [x] 4.6 Floor configurable: override `settings.ENV_FLOOR` (monkeypatch) to `["PATH"]` and assert only `PATH` passes
- [x] 4.7 Bare exec no longer inherits the full parent env — `MCC_TEST_SECRET` absent, `PATH` present (update/extend existing `test_env_passthrough_false_excludes_parent_env`)
- [x] 4.8 Update `test_py_callable_env`: drop the `env_passthrough=True` "so imports work" workaround; verify the floor + `PYTHONPATH` keep the fn importable
- [x] 4.9 fn introspection does not leak: load an fn tool with `env_passthrough: false` and a parent secret set; assert the introspect subprocess env excludes it (spy on `subprocess.run` env, or assert via a fn that echoes its env)

## 5. Docs

- [x] 5.1 `docs/tools/yaml-format.md`: update the `env_passthrough` row — type `bool | list[str]`, note the floor
- [x] 5.2 `docs/tools/env-vars.md`: rewrite the `env_passthrough:` section — document `false` (floor only), list allowlist with `fnmatchcase` globs, `true` (firehose, discouraged), and the configurable floor; reconcile the existing `PATH`/import claims which only become true with this change
- [x] 5.3 `docs/tools/python.md`: update the fn `env_passthrough` import note to reference the floor + allowlist instead of `env_passthrough: true`

## 6. Verify

- [x] 6.1 `uv run pytest tests/`
- [x] 6.2 `uv run ruff check` and `uv run pyright` (per AGENTS.md, run all three)
- [x] 6.3 Sanity-load `mcc/tools/public.yaml` — confirm no tool silently depended on a non-floor inherited variable
