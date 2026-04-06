## Why

Exec tool commands are currently formatted with `str.format()` after blanket `shlex.quote()`-ing every parameter, which makes it impossible to pass raw flags, iterate over list arguments, or apply conditional logic in the command template. Jinja2 is already a project dependency and provides all of this with a simple `| quote` filter for explicit shell quoting.

## What Changes

- **BREAKING**: `exec:` field in tool YAML now uses Jinja2 template syntax (`{{ param | quote }}`) instead of Python format strings (`{param}`)
- New `| quote` filter: quotes a scalar with `shlex.quote`; for a list, quotes each element and joins with spaces
- All existing exec tool YAML fixtures updated to Jinja syntax
- Docs updated to cover the new syntax, the `| quote` filter, and the EnvYAML `${VAR}` / Jinja `{{ }}` composition pattern
- Tests added covering: scalar quoting, list quoting, conditional blocks, missing variable errors, and the EnvYAML coexistence case

## Capabilities

### New Capabilities

- `exec-jinja-templates`: Jinja2-based command templating for exec tools, including the `| quote` filter and `StrictUndefined` error behavior

### Modified Capabilities

- `exec-tool`: requirement change — command interpolation is now template-based rather than format-string-based; quoting is opt-in via `| quote` rather than applied to all params unconditionally

## Impact

- `mcc/exec.py`: replace `shlex`+`str.format` with Jinja2 environment + custom filter
- `tests/fixtures/tools_exec_interpolate.yaml` and related fixtures: syntax update
- `tests/test_exec.py`: new test cases for Jinja features
- `docs/`: new or updated page covering exec tool templating
