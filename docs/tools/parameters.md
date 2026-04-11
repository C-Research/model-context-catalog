---
icon: lucide/sliders
---

# Parameters

Parameters define the inputs a tool accepts. They're validated before execution — required params must be present, types are coerced, and overrides are injected. For `fn` tools, params can be omitted and introspected from the function signature (see [Python Tools](python.md)). For `exec` tools, they must always be declared explicitly.

## Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | yes | Argument name — must match the function parameter or template variable |
| `type` | no | One of: `str`, `int`, `float`, `bool`, `list`, `dict` (default: `str`) |
| `required` | no | Whether the caller must supply a value (default: `true`) |
| `default` | no | Default value used when the param is not required |
| `description` | no | Shown to the LLM in the tool signature — be specific |
| `example` | no | A concrete example value shown to the LLM alongside the description |
| `override` | no | Always injects this value; hidden from the LLM and callers |

!!! tip "Description and example directly affect LLM behavior"
    The LLM has no other context for what a parameter means or what values are valid — only what you write here. Vague or missing descriptions cause the LLM to guess, leading to incorrect calls or repeated failures. Write `description` as if explaining to a colleague who has never seen your system, and use `example` to anchor the expected format for anything non-obvious (dates, IDs, query syntax, etc.).

```yaml
params:
  - name: query
    type: str
    required: true
    description: Natural language search query
    example: "recent errors in auth service"

  - name: limit
    type: int
    required: false
    default: 10
    description: Maximum number of results to return
```

## Overrides

An `override` parameter is injected at call time and never exposed to the LLM. Use it for secrets, fixed configuration, or tenant IDs that callers should not control.

```yaml
params:
  - name: api_key
    type: str
    override: "${MY_API_KEY}"   # env var substituted at load time

  - name: tenant
    type: str
    override: "acme-corp"       # literal value
```

Override values do not appear in the tool signature. The LLM has no knowledge they exist.
