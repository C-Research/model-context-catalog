## Context

`env_passthrough` controls the *base* environment a tool's subprocess starts from, before `env_file` and `env` are overlaid. Today it is a bool with two settings (empty base vs. full `os.environ`) and a hidden third behavior: when `_build_env` returns `None`, both the exec path (OS-default inheritance) and the fn/pyrunner path (`os.environ` fallback) leak the full parent environment regardless of the flag.

This change introduces a middle mode (an allowlist), an always-present floor of safe variables, and removes the `None` sentinel that caused the leaks.

## Goals / Non-Goals

**Goals:**
- `env_passthrough: bool | list[str]` — list is a case-sensitive glob allowlist over `os.environ` keys.
- A configurable, always-applied env floor so default-deny tools (exec/curl/fn) still function.
- `env_passthrough: false` genuinely denies everything outside the floor on both exec and fn paths.
- Introspect-time and call-time environments are identical for fn tools.

**Non-Goals:**
- Regex/brace-expansion patterns (globs only).
- Per-tool floor overrides or a way to drop below the floor.
- Any change to overlay precedence (`env` > `env_file` > base) or to resource limits / cwd handling.

## Decisions

### 1. Type: `bool | list[str]`

```
ToolModel.env_passthrough: bool | list[str] = False
```

Pydantic resolves the union from YAML cleanly (`false`, `true`, or `["AWS_*", "HOME"]`). `[]` is a valid empty allowlist and is behaviorally identical to `false` (floor only) — no special-casing needed. `true` and a list are mutually exclusive by construction (it is one value), so no validator guard is required.

The existing truthiness guard works for lists by luck — but the guard is being deleted anyway (see Decision 4), so this is moot.

### 2. Glob matching: `fnmatchcase`

Allowlist entries are matched against `os.environ` keys with `fnmatch.fnmatchcase` — **case-sensitive**. Env var names are conventionally uppercase; case-insensitive matching (`fnmatch.fnmatch`, which uses `os.path.normcase`) would let `path` match `PATH` on some platforms. Exact names (`"HOME"`) are just globs with no wildcards, so the allowlist subsumes the sudo `env_keep` exact-match model for free.

```python
from fnmatch import fnmatchcase
matched = {k: v for k, v in os.environ.items()
           if any(fnmatchcase(k, pat) for pat in env_passthrough)}
```

### 3. The env floor

A deployment-wide list of variable names always merged into the base, regardless of `env_passthrough`. It is the "machine works" set, not secrets.

```
settings.yaml
default:
  env_floor:
    - PATH
    - HOME
    - USER
    - LOGNAME
    - TMPDIR
    - LANG
    - LC_ALL
    - TZ
    - TERM
    - SHELL
```

Read via `settings.ENV_FLOOR` (dynaconf). Overridable per deployment through `settings.local.yaml`, `MCC_ENV_FLOOR`, or `dynaconf_merge` — the same mechanisms as every other setting. A variable in the floor is only included if actually present in `os.environ` (a floor entry that the server process doesn't have is silently skipped, not set to empty).

**The floor is always exposed, even when `env_passthrough: false`.** This is deliberate: `false` means "deny secrets," not "empty env." There is intentionally no way to drop below the floor — a tool that wants a literally empty environment is out of scope. The trade-off: `false` no longer means "truly nothing," it means "floor only." Accepted, because a subprocess with zero env (no `PATH`) is rarely useful and the floor contains no secrets.

**Alternative considered — hardcoded constant.** Rejected: this is a security/policy surface; deployments legitimately differ (some want `TZ`, some want to harden by removing `HOME`). Settings-configurable matches the project's dynaconf convention and the user's explicit ask.

### 4. `_build_env` never returns `None`

This is the core of the leak fix. Today:

```python
if not env and not env_file and not env_passthrough:
    return None                      # ← the leak sentinel
merged = dict(os.environ) if env_passthrough else {}
...
```

`None` propagates two ways: exec passes `env=None` to the subprocess (OS inherits everything), and `_build_pyrunner_env` does `dict(base if base is not None else os.environ)`. Both leak.

New shape — always returns a concrete dict, floor-first:

```python
def _build_env(env, env_file, env_passthrough=False):
    floor = settings.ENV_FLOOR
    base = {k: os.environ[k] for k in floor if k in os.environ}

    if env_passthrough is True:
        base = dict(os.environ)                       # firehose; floor ⊆ this
    elif isinstance(env_passthrough, list):
        base |= {k: v for k, v in os.environ.items()
                 if any(fnmatchcase(k, p) for p in env_passthrough)}
    # False → base stays = floor

    if env_file:
        base |= {k: v for k, v in dotenv_values(env_file).items() if v is not None}
    if env:
        base |= env
    return base
```

The early `if not env and not env_file and not env_passthrough: return None` guard is **deleted**. Every caller now receives a real dict, so:

- `make_exec_callable` passes a concrete env to the subprocess — bare exec no longer inherits the full environment; it gets the floor.
- `_build_pyrunner_env` simplifies to `result = dict(base)` (no `os.environ` fallback), then injects its python-specific additions on top.

Note `env_passthrough is True` (identity) not truthiness, so a non-empty list does not accidentally hit the firehose branch.

### 5. fn introspection honors the setting

`models.py` introspect validator currently hardcodes `False`:

```python
"env": _build_pyrunner_env(self.env, self.env_file, False, effective_cwd)
```

Becomes:

```python
"env": _build_pyrunner_env(self.env, self.env_file, self.env_passthrough, effective_cwd)
```

Now the load-time introspect subprocess sees exactly what the call-time subprocess will see — no more divergence, and no full-env leak during introspection. Because the floor includes the import-critical basics and `_build_pyrunner_env` always injects `PYTHONPATH=cwd`, the common fn tool still introspects without ceremony.

### 6. Python import vars: floor vs. pyrunner-injected

`_build_pyrunner_env` already injects `PYTHONPATH` (prepends `cwd`) and sets `MCC_SKIP_AUTOLOAD` unconditionally — those stay. The universal `env_floor` is kept as pure "OS basics" and does **not** include `VIRTUAL_ENV`/`PYTHONHOME`; if a fn tool's import needs a venv marker, the author adds it via allowlist (`env_passthrough: ["VIRTUAL_ENV"]`). 

Rationale: in normal operation `python` is `sys.executable` (the mcc venv), whose installed packages and editable installs are importable without `VIRTUAL_ENV`, and `PYTHONPATH=cwd` covers the tool's own module. Keeping venv markers out of the universal floor avoids handing every exec tool variables it has no use for. (Open to folding `VIRTUAL_ENV` into the floor if real tools need it — left as the one soft spot.)

## Risks / Trade-offs

**Behavior change — bare exec/fn lose the full-env inheritance.** Any existing tool that silently relied on inheriting a non-floor parent variable (a custom `PYTHONPATH` entry, a venv marker, an app config var) will stop seeing it. Mitigation: the floor covers `PATH`/`HOME`/locale/tmp — the overwhelmingly common needs — and anything else is one allowlist entry. This is the intended security fix, surfaced at load time for fn tools (introspect uses the same env), so misconfigurations fail fast and visibly.

**`curl:` tools depend on `PATH` to find the curl binary.** `PATH` is in the default floor, so curl tools work out of the box. A deployment that removes `PATH` from the floor breaks them — documented.

**`false` no longer means empty.** A caller wanting true isolation cannot get it via `env_passthrough`. Out of scope by design; the floor is always exposed.

**Settings dependency in `exec.py`.** `_build_env` reads `settings.ENV_FLOOR`. `exec.py` already imports from `mcc.settings` (the logger), so this introduces no new coupling. Tests that construct `ToolModel` directly will read the default floor from `settings.yaml` unless overridden.
