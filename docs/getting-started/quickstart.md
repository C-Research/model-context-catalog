---
icon: lucide/zap
---

# Quick Start

This guide gets MCC running with a simple tool in under five minutes.

## 1. Define a tool

Create `mytools.yaml`:

```yaml
groups: [public]
tools:
  - fn: mypackage.utils:greet
    description: Greets a user by name
```

Where `mypackage/utils.py` contains:

```python
def greet(name: str) -> str:
    """Returns a greeting for the given name."""
    return f"Hello, {name}!"
```

## 2. Register it

In `settings.local.yaml`:

```yaml
tools:
  - mytools.yaml
```

## 3. Start the server

Default transport is SSE which is easiest for development

```bash
mcc mcp serve
```

## 4. Connect Claude

Configure Claude to locate mcc. Easiest way is to use mcp-proxy in `claude_desktop_config.json`

```json
{
  "mcpServers": {
    "model-context-catalog (mcc)": {
      "command": "mcp-proxy",
      "args": [
        "http://localhost:8000/sse"
      ]
    }
  }
}
```

Restart Claude and now you can say `greet someone named Alice` which will perform

```
search("greet someone") → finds public.greet
execute("public.greet", {"name": "Alice"}) → "Hello, Alice!"
```

## Next steps

- [YAML Tool Format](../tools/yaml-format.md) — full reference for tool definitions
- [Parameters](../tools/parameters.md) — types, defaults, and overrides
- [Users & Groups](../auth/users-groups.md) — restrict tool access
