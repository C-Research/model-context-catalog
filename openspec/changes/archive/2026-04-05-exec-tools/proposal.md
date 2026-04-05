## Why

The tool catalog currently only supports Python callables via `fn:`. This limits tool authors to Python and forces everything into the same process. Adding an `exec:` field lets tool definitions run external commands — any language, any binary — turning the catalog into a polyglot tool bus.

## What Changes

- Add `exec: str` field to `ToolModel` as an alternative to `fn:` (one or the other, not both)
- Add `stdin: bool = False` field — when true, params are sent as a JSON blob on stdin; when false (default), params are interpolated into the command string via `{param_name}`
- Add `timeout: int | None` field — optional seconds limit for exec tools, enforced via `asyncio.wait_for`
- Add `limits: dict | None` field — optional resource limits (`mem_mb`, `cpu_sec`, `fsize_mb`, `nofile`) enforced via `preexec_fn` + `resource` module (unix only)
- Exec tools always return `(returncode, stdout, stderr)` tuple, matching the existing `bash()` contrib signature
- Exec tools require params to be declared in YAML (no Python signature to introspect)
- `callable` property generates an async subprocess wrapper instead of importing a Python function
- ⚠ **Security note**: With `stdin: false`, parameters are interpolated directly into the shell command. Exec tools with user-controlled params should not be exposed to untrusted callers without input validation.

## Capabilities

### New Capabilities
- `exec-tool`: Subprocess-based tool execution with stdin/interpolation modes, timeout, resource limits, and structured `(returncode, stdout, stderr)` return values

### Modified Capabilities
- `tool-catalog`: ToolModel gains `exec`, `stdin`, and `timeout` fields; validation enforces fn-or-exec exclusivity; `callable` and `introspect` branch on tool type

## Impact

- `mcc/models.py` — ToolModel fields, introspect validator, callable property, signature formatting
- `mcc/loader.py` — no changes expected (already passes YAML fields through to ToolModel)
- Tests — new test file for exec tools covering both stdin and interpolation modes
- Docs — document the exec tool YAML format and security considerations
