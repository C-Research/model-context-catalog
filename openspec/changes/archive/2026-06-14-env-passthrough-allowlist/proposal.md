## Why

`env_passthrough` is a coarse boolean: `false` (subprocess gets only explicitly declared env) or `true` (subprocess inherits the entire parent environment). There is no way to expose a *specific* set of parent variables — the sudo `env_keep` model — so authors who need one inherited variable are forced to choose `true` and leak every secret the server process holds (API tokens, cloud credentials, `MCC_*` settings).

Worse, `false` does not actually mean "deny" today. Two code paths leak the full parent environment regardless of the flag:

- **fn introspection** (`models.py`) calls `_build_pyrunner_env(..., False, ...)` with a hardcoded `False`; `_build_env` returns `None` for the unconfigured case, and `_build_pyrunner_env` then falls back to `dict(os.environ)` — so every fn tool runs its load-time introspect subprocess with all secrets in env.
- **bare exec** (`exec: ...` with no env/env_file and `passthrough: false`) produces `env=None`, so the OS hands the subprocess the full inherited environment.

So `env_passthrough: false` is a lie on both paths. This change makes it true.

## What Changes

- `env_passthrough` accepts `bool | list[str]`. A list is an allowlist of parent variable names; each entry is an `fnmatchcase` glob (case-sensitive) matched against `os.environ` keys — e.g. `["AWS_*", "GIT_*", "HOME"]`.
- A configurable **env floor** (`env_floor` in settings) is always merged into every subprocess environment, even when `env_passthrough` is `false`. Default floor: `PATH, HOME, USER, LOGNAME, TMPDIR, LANG, LC_ALL, TZ, TERM, SHELL`. This keeps exec/curl/fn tools functional under default-deny without leaking secrets.
- `_build_env` **never returns `None`** — it always returns a concrete dict (floor + mode + overlays). This closes both leaks at the source: there is no longer a `None` value that triggers an `os.environ` fallback or OS-default inheritance.
- fn introspection honors `self.env_passthrough` instead of hardcoded `False`. Introspect-time env now equals call-time env, so a tool whose import needs an allowlisted/floor variable is consistent at load and at call, and the load-time introspect subprocess no longer leaks the full environment.
- No back-compat shims. `false` (and unset) now mean "floor only." Existing tools relying on the implicit full-environment leak must declare what they need via the floor (already covers `PATH`/`HOME`/etc.) or an explicit allowlist.

## Capabilities

### Modified Capabilities

- `exec-tool`: `env_passthrough` becomes `bool | list[str]`; bare exec tools no longer inherit the full parent environment — they receive the configurable env floor plus any allowlisted/declared variables.
- `isolated-python-tool`: fn introspection and execution both honor `env_passthrough`; the load-time introspect subprocess no longer leaks the full parent environment.

## Impact

- `mcc/models.py`: `env_passthrough: bool | list[str] = False`; introspect validator passes `self.env_passthrough` (not `False`) to `_build_pyrunner_env`.
- `mcc/exec.py`: `_build_env` three-way branch (False → floor; list → floor + `fnmatchcase` matches; True → full `os.environ`), reads `settings.ENV_FLOOR`, never returns `None`; delete the early `return None` guard; `_build_pyrunner_env` drops its `os.environ` fallback (`dict(base)`); signatures change `env_passthrough: bool` → `bool | list[str]`.
- `mcc/settings.yaml`: add `env_floor:` list under `default:`.
- `mcc/tools/public.yaml` and any catalog: tools relying on the implicit full-env leak need an explicit allowlist (most need nothing — the floor covers `PATH`/`HOME`).
- `docs/tools/env-vars.md`: rewrite the `env_passthrough` section — document `bool | list[str]`, the floor, and reframe `true` as the discouraged firehose; several existing claims about `false` (no `PATH`) only become true with this change.
- Tests: `test_exec.py` env cases (the `env_passthrough=True` "so imports work" workaround at `test_py_callable_env` can drop, since the floor now covers imports).

## Non-Goals

- Regex or shell-style brace expansion in the allowlist — `fnmatchcase` globs only (`*`, `?`, `[seq]`).
- Per-tool override of the floor — the floor is a single deployment-wide setting; a tool cannot shrink it below the floor (the floor is always exposed by design).
- Connection pooling / persistent subprocesses — unchanged.
