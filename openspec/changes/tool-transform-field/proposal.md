## Why

Tools that fetch remote content (HTML, XML, JSON) often return large payloads that bloat LLM context and reduce signal quality. There is no declarative way to filter or compact tool output at definition time — the full payload always reaches the LLM.

## What Changes

- Add an optional `transform` field to tool YAML definitions (both `exec`/`curl` and `fn` tools)
- `transform` is a shell command string or list of shell command strings; lists are joined with `|` into a single pipeline
- The transform value is Jinja-templated using the same tool kwargs as the main command
- For `exec`/`curl` tools: the transform pipeline is appended to the existing command in the same subprocess
- For `fn` tools: the transform runs as a separate subprocess after pyrunner exits, with the fn's JSON output piped as stdin
- If the original tool call fails (non-zero exit or error tuple), the transform is **not** applied — the error passes through unchanged
- Transform inherits the tool's `timeout`; it does not inherit `env`

## Capabilities

### New Capabilities

- `tool-transform`: Optional postprocessing pipeline on tool output via shell commands

### Modified Capabilities

<!-- None — purely additive -->

## Impact

- `mcc/models.py`: new `transform` field on `ToolModel`; passed into `make_exec_callable` and `make_py_callable`
- `mcc/exec.py`: `make_exec_callable` appends transform to command; `make_py_callable` gains `_apply_transform` helper
- `tests/`: new fixture and test coverage for transform behavior
- No new dependencies; no breaking changes
