## 1. Update execute() handler

- [x] 1.1 Add `ctx: Context` parameter to `execute()` in `mcc/app.py` (import `Context` from `fastmcp`)
- [x] 1.2 Add imports: `create_model` from pydantic, `Field` from pydantic, elicitation result types from `fastmcp.server.elicitation`
- [x] 1.3 Implement pre-call check: collect missing required primitive params not present in `params or {}`
- [x] 1.4 Build dynamic `MissingModel` via `create_model` using `Field(..., description=p.description)` for each missing param
- [x] 1.5 Call `ctx.elicit()` with a descriptive message listing missing param names/types and the `MissingModel`
- [x] 1.6 On `AcceptedElicitation`: merge `result.data.model_dump()` into params dict and continue to `tool.call()`
- [x] 1.7 On `DeclinedElicitation` or `CancelledElicitation`: return `"Execution cancelled: required parameters not provided"`
- [x] 1.8 Wrap the entire elicitation block in `try/except Exception` to fall through to existing `tool.call()` path when client doesn't support elicitation

## 2. Tests

- [x] 2.1 Add test: missing primitive param → elicitation accepted → tool executes successfully
- [x] 2.2 Add test: missing primitive param → elicitation declined → returns "Execution cancelled"
- [x] 2.3 Add test: missing primitive param → elicitation cancelled → returns "Execution cancelled"
- [x] 2.4 Add test: missing primitive param → elicitation raises (unsupported client) → falls through to ValidationError
- [x] 2.5 Add test: missing list/dict param → elicitation skipped → ValidationError returned
- [x] 2.6 Add test: all required params provided → elicitation not triggered

## 3. Verify

- [x] 3.1 Run `uv run pytest tests/` — all tests pass
- [x] 3.2 Run `uv run ruff check mcc/` — no lint errors
- [x] 3.3 Run `uv run pyright mcc/` — no type errors
