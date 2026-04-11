## Why

Tool YAML files with many entries (e.g. an OSINT catalog with 20+ tools) currently require repeating `env_file` on every `fn:` tool, and for `curl:` tools the per-tool `env_file` does nothing useful since `${VAR}` references are expanded at load time anyway. A file-level `env_file` and `env` block eliminates this repetition and makes the relationship between a catalog file and its secrets explicit.

## What Changes

- `load_file()` in `mcc/loader.py` gains a two-pass read: a first cheap YAML parse extracts top-level `env_file` and `env`, loads them into the environment, then the full `EnvYAML` parse runs with those vars available for `${VAR}` expansion
- Top-level `env_file` and `env` values cascade down to all tools in the file; per-tool `env_file`/`env` merge on top (tool-level wins on key conflicts)
- No changes to `ToolModel` — the cascade is resolved at load time before constructing models

## Capabilities

### New Capabilities
- `yaml-file-env`: File-level `env_file` and `env` fields in tool YAML that apply to all tools in the file, with per-tool values taking precedence

### Modified Capabilities
- `catalog-loader`: Load pipeline gains a pre-pass to extract and inject file-level env before `EnvYAML` parsing

## Impact

- `mcc/loader.py`: `load_file()` function
- `osint/search.yaml`: can drop per-tool `env_file: osint.env`, move to top-level
- No API changes, no breaking changes to existing YAML files (fields are additive)
