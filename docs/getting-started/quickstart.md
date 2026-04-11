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

```bash
mcc serve
```

## 4. Connect Claude

Point your MCP client at `http://localhost:8000`. Claude can now:

```
search("greet someone") → finds public.greet
execute("public.greet", {"name": "Alice"}) → "Hello, Alice!"
```

## Next steps

- [YAML Tool Format](../tools/yaml-format.md) — full reference for tool definitions
- [Parameters](../tools/parameters.md) — types, defaults, and overrides
- [Users & Groups](../auth/users-groups.md) — restrict tool access
