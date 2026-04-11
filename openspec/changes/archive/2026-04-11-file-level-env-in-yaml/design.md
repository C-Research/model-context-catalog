## Context

`mcc/loader.py:load_file()` uses `EnvYAML(path, strict=False)` to parse tool YAML files. EnvYAML expands `${VAR}` syntax from `os.environ` at parse time — so any `${VAR}` in a curl template or `override:` field is baked into the tool definition immediately on load. Currently `env_file` and `env` are per-`ToolModel` fields; the loader passes them straight through to the tool's subprocess environment but does nothing with them at parse time. This means file-level secret injection has no first-class support.

## Goals / Non-Goals

**Goals:**
- Support top-level `env_file` and `env` fields in tool YAML files
- These are resolved before `EnvYAML` parses the file, so `${VAR}` references anywhere in the file see those vars
- Per-tool `env_file`/`env` continue to work and take precedence (tool-level merges on top of file-level)
- No changes to `ToolModel` — cascade is fully resolved at load time

**Non-Goals:**
- Hierarchical / inherited env files (no "env_file inherits from parent dir" behaviour)
- Runtime re-injection of file-level env vars (they're load-time only, same as now)
- Validating that referenced env vars are present (EnvYAML `strict=False` already permits missing vars)

## Decisions

### Two-pass parse in `load_file()`

**Decision**: Do a first cheap `yaml.safe_load()` pass to extract `env_file` and `env` from the raw YAML, inject those vars into a temporary env overlay, then call `EnvYAML` with that overlay.

**Why not just set `os.environ` directly**: Mutating global process env is not thread-safe and pollutes the namespace for other concurrent loads.

**How to overlay**: EnvYAML's constructor accepts an `env` dict parameter (`EnvYAML(path, env=..., strict=False)`) which merges on top of `os.environ` for `${VAR}` resolution. We build that dict as: `{**dotenv_values(env_file), **env_block}`, where `env_block` is the top-level `env:` mapping. Tool-level `env_file`/`env` are passed through to `ToolModel` unchanged — they control subprocess environment, not load-time expansion.

**Alternatives considered**:
- `os.environ` mutation with cleanup: simpler but not safe for concurrent loads
- Requiring users to use `mcc serve --env-file`: already works but forces an out-of-band invocation step; loses colocation of catalog + secrets config

### Merge precedence

File-level env_file vars < file-level env vars < process `os.environ` < tool-level env_file / tool-level env.

Process env always wins at load time (EnvYAML behaviour). Tool-level env_file/env continue to control subprocess environment at execution time, independent of load-time expansion.

### No `ToolModel` changes

The cascade happens entirely in `load_file()`. `ToolModel` already carries `env_file` and `env` for subprocess use; we do not add a concept of "inherited" env to the model.

## Risks / Trade-offs

- **`yaml.safe_load` sees raw `${VAR}` strings**: The first pass intentionally does no expansion — we only need the literal `env_file` path and `env` dict values, which should never themselves contain `${VAR}`. If they do, they're treated as literals in the first pass (acceptable).
- **EnvYAML `env=` parameter availability**: This parameter exists in `envyaml >= 1.2.0`. If an older version is pinned, fallback is a temporary `os.environ` mutation with try/finally cleanup.
- **`dotenv_values` for the first-pass env_file load**: Already imported in `exec.py`; reuse the same import in `loader.py`.

## Migration Plan

Additive change — existing YAML files with no top-level `env_file`/`env` are unaffected. To migrate an existing file:

1. Remove per-tool `env_file: path/to/secrets.env` entries
2. Add `env_file: path/to/secrets.env` at the top level
3. Reload; `${VAR}` expansion continues to work identically

No rollback needed — removing the top-level field restores previous behaviour.

## Open Questions

- Should `env_file` path be resolved relative to the YAML file's directory or the working directory? **Proposal**: relative to the YAML file's directory (consistent with how tool `cwd` works), with absolute paths also accepted.
