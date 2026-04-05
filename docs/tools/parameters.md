# Parameters

Parameters can be declared explicitly in YAML or introspected automatically from the function signature.

## Auto-introspection

If you omit `params`, MCC reads them from the function's type annotations:

```python
def search_docs(query: str, limit: int = 10) -> list[str]:
    ...
```

```yaml
tools:
  - fn: mymodule:search_docs
    # params auto-inferred:
    #   query: str, required
    #   limit: int, default 10
```

## Explicit params

```yaml
params:
  - name: query
    type: str
    required: true
    description: The search query

  - name: limit
    type: int
    required: false
    default: 10
    description: Maximum number of results
```

## Parameter fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | yes | Argument name, must match the function parameter |
| `type` | no | One of: `str`, `int`, `float`, `bool`, `list`, `dict` |
| `required` | no | Whether the caller must supply a value (default: `true`) |
| `default` | no | Default value used when `required: false` |
| `description` | no | Shown to the LLM in the tool signature |
| `override` | no | Always injects this value; hidden from callers |

## Overrides

An `override` parameter is injected at call time and hidden from the LLM. Useful for injecting secrets, tenant IDs, or fixed configuration that callers should not control.

```yaml
params:
  - name: api_key
    type: str
    override: "${MY_API_KEY}"   # env var substitution supported

  - name: tenant
    type: str
    override: "acme-corp"       # literal value
```

!!! warning
    Override values are not visible in the tool signature shown to the LLM. Callers cannot supply or override them.
