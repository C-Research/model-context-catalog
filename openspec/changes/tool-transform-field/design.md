## Context

Tools return raw subprocess stdout or fn return values to the LLM. When a tool fetches HTML, XML, or large JSON payloads, the entire content lands in the LLM's context window. There is no existing hook between execution and return to compact or filter output.

`exec`/`curl` tools run via `make_exec_callable` (shell subprocess). `fn` tools run via `make_py_callable` (pyrunner subprocess) and emit JSON on stdout. Both paths converge at `_communicate_and_return`, which returns either `str` (success) or `tuple[int, str, str]` (failure).

## Goals / Non-Goals

**Goals:**
- Declarative `transform` field on any tool (exec, curl, fn)
- Shell pipeline(s) applied to output before it reaches the LLM
- Jinja-templated transform values (kwargs available, same as exec command)
- Skip transform on tool failure — errors pass through unchanged
- Inherit tool timeout; no env inheritance

**Non-Goals:**
- Python fn-based transforms (shell only for now)
- Per-step timeouts within the transform pipeline
- Transform env isolation or sandboxing beyond the tool's existing limits

## Decisions

### 1. Shell-only transforms

Shell commands cover the primary use cases (jq, xmllint, pup, html2text, sed, awk, head) without requiring new Python dependencies or a fn-resolution path. A Python fn transform layer can be added later if needed.

**Alternative considered**: Dict-style `{fn: mcc.contrib.text:xpath, expr: "//p"}` items in the pipeline. Rejected: more complex parsing, requires in-process fn loading, and shell covers the same cases with existing tools.

### 2. String or list, joined with `|`

`transform` accepts a plain string or a list of strings. A list is joined with ` | ` at load time. This lets users express multi-step pipelines readably without escaping `|` inside a quoted string.

```yaml
transform: "jq -r '.items[]'"                          # string
transform:                                              # list
  - "jq -r '.items[]'"
  - "head -c 8000"
```

### 3. Exec tools: append to same subprocess pipeline

For exec/curl tools, the transform is appended to the rendered command string before the subprocess starts:

```python
run_cmd = f"({run_cmd}) | {transform}"
```

This keeps everything in one subprocess and avoids the overhead of a second process. The parentheses protect against edge cases where the original command ends with a redirect or background operator.

### 4. Fn tools: separate subprocess after pyrunner

pyrunner emits JSON on stdout. After `_communicate_and_return` returns a `str`, a new `subprocess_shell` is spawned with the transform command and the pyrunner output piped as stdin. Two subprocesses are necessary because pyrunner uses a different Python interpreter and its stdout is already captured.

### 5. Skip transform on failure

`_communicate_and_return` returns `str` on success, `tuple[int, str, str]` on failure. The transform is only applied when the result is a `str`. This prevents transform errors from obscuring the real error, and avoids piping garbage into filters that expect well-formed input.

### 6. No env inheritance

Transforms are text-munging pipelines (jq, grep, sed, etc.) that operate on stdout. They do not need API keys or secrets. Keeping env out of transforms avoids accidentally exposing secrets to shell commands the user may not fully control.

## Risks / Trade-offs

- **Shell injection via Jinja rendering** → Same risk surface as the `exec` field. Transform values live in tool YAML files controlled by the operator, not end-user input.
- **Transform failure is indistinguishable from tool failure** → Non-zero exit from the transform returns `(code, stdout, stderr)` like any other failure. Error message in stderr will typically identify the failing command.
- **Single timeout budget shared** → A slow tool + slow transform could use the full timeout before either completes. Acceptable for now; per-step timeouts are a non-goal.
