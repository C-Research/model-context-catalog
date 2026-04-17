## Why

When a user calls `execute()` with missing required parameters, the tool currently returns a raw `ValidationError` string — a dead end that forces the caller to re-invoke with corrected params. FastMCP's `ctx.elicit()` provides a first-class mechanism to interactively request missing input, turning a failure into a guided continuation.

## What Changes

- `execute()` in `app.py` gains a `ctx: Context` parameter (FastMCP auto-injects it)
- Before calling `tool.call()`, missing required primitive params are identified and collected
- A dynamic Pydantic model is built from the missing params and passed to `ctx.elicit()`
- Accepted responses are merged into `params` and execution proceeds
- Declined/cancelled responses return `"Execution cancelled: required parameters not provided"`
- If the client does not support elicitation (exception), falls through to the existing `ValidationError` path
- Only `str`, `int`, `float`, `bool` params are elicitable; `list`/`dict` missing params fall through to the existing error

## Capabilities

### New Capabilities
- `execute-elicitation`: Interactive elicitation of missing required primitive parameters during tool execution

### Modified Capabilities
- `execute-tool`: The execute handler's behavior for missing required params changes — elicitation is attempted before returning a validation error

## Impact

- `mcc/app.py`: `execute()` handler modified
- No changes to `ToolModel`, `ParamModel`, or any auth/middleware logic
- Requires FastMCP version that supports `ctx.elicit()` (already in use)
- Elicitation is only triggered for MCP clients that support the elicitation protocol
