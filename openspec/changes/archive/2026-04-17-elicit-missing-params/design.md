## Context

The `execute()` handler in `mcc/app.py` currently returns a raw `ValidationError` string when required parameters are missing. FastMCP provides `ctx.elicit()` to interactively request missing input from the client during tool execution. This change wires elicitation into the execute handler as a pre-call step.

`ToolModel` already exposes everything needed: `visible_params` (list of `ParamModel` with `name`, `type`, `required`, `description`) and `param_model` (a `create_model`-built Pydantic class). No changes to the model layer are required.

## Goals / Non-Goals

**Goals:**
- Elicit missing required primitive (`str`, `int`, `float`, `bool`) params before calling the tool
- Merge accepted elicitation response into params and proceed with execution
- Gracefully handle declined, cancelled, or unsupported elicitation (fall through to existing error)

**Non-Goals:**
- Eliciting `list` or `dict` params (MCP elicitation schema only supports primitives)
- Eliciting params that were already provided (even if the value is wrong)
- Modifying `ToolModel`, `ParamModel`, or any auth/middleware code

## Decisions

### 1. Pre-validation check, not post-ValidationError

Identify missing params by inspecting `tool.visible_params` against the provided `params` dict before calling `tool.call()`. This is explicit and predictable.

**Alternative**: Catch `ValidationError`, parse it for missing fields, then elicit. Rejected — fragile, depends on Pydantic error message format, and can't distinguish "missing" from "wrong type."

### 2. Primitives only

Only params with `type in ("str", "int", "float", "bool")` are included in the elicitation schema. Missing `list`/`dict` params are not elicited — they fall through to the existing `ValidationError` path.

**Alternative**: Serialize complex types as JSON strings in elicitation. Rejected — poor UX, error-prone.

### 3. ctx.elicit() wrapped in try/except

If the client doesn't support elicitation, `ctx.elicit()` will raise. Wrap it in a broad `except Exception` and fall through to the existing `tool.call()` path (which will raise `ValidationError`).

### 4. Build model for missing params only

```python
missing = [
    p for p in tool.visible_params
    if p.required
    and p.name not in (params or {})
    and p.type in ("str", "int", "float", "bool")
]
fields = {p.name: (p.py_type, Field(..., description=p.description)) for p in missing}
MissingModel = create_model("MissingParams", **fields)
result = await ctx.elicit(
    f"Tool '{key}' requires additional parameters",
    MissingModel,
)
```

`AcceptedElicitation.data` is the model instance; `.model_dump()` gives the dict to merge.

### 5. Elicitation message includes param names and types

The message passed to `ctx.elicit()` lists the missing params with type and description, e.g.:

> `Tool 'admin.shell' requires: command (str) — Shell command to run`

This gives the client UI enough context even before the user fills the schema form.

## Risks / Trade-offs

- [Client support] Not all MCP clients support elicitation → Mitigated by try/except fallback
- [Partial elicitation] If some missing params are `list`/`dict` and others are primitive, the primitive ones are elicited but the complex ones still fail → Acceptable; error message on `ValidationError` will clarify what's still missing
- [ctx injection] Adding `ctx: Context` to `execute()` is a FastMCP convention — no concerns, but it's a visible signature change
