# Python Tools

Python tools wrap any importable callable — a function, method, class, or `async` awaitable. MCC introspects the callable at load time to populate `name`, `description`, and `params` automatically.

## Defining a tool

Write a new python function ready to go (or use one from somewhere else)

```python
# mypackage/utils.py
def greet(name):
    return f'Hi {name}'
```

Then use that function in your tool spec

```yaml
tools:
  - fn: mypackage.utils:greet
```

That's the minimum. Everything else is inferred from the function itself!

## `fn` syntax

Use colon notation to separate the module path from the attribute:

```yaml
fn: mypackage.mymodule:my_function        # preferred
fn: mypackage.mymodule.my_function        # dot notation also works
fn: mypackage.mymodule:MyClass.my_method  # nested attribute access
```

The module is imported with `importlib.import_module`, then each attribute after the colon (or the final dot segment) is resolved with `getattr`. Any importable Python object works — including stdlib modules:

```yaml
- name: regex_search
  fn: re:findall
  params:
    - name: pattern
      type: str
    - name: string
      type: str
```

## Introspection

When a `fn` tool loads, MCC inspects the callable to fill in any missing fields:

!!! tip "Be explicit"

    It is always better to specify values in the tool spec itself to tailor to the LLM audience. Docstrings are for devs, descriptions are for LLMs

| Field | Source | Notes |
|-------|--------|-------|
| `name` | `callable.__name__` | Override in YAML to change the catalog key |
| `description` | `callable.__doc__` | Full docstring — sent to the LLM, so quality matters |
| `params` | `inspect.signature(callable)` | One param entry per argument; `*args` and `**kwargs` are skipped |
| param `type` | Parameter annotation | Maps to `str`, `int`, `float`, `bool`, `list`, `dict`. Unannotated defaults to `str` |
| param `required` | Presence of a default value | No default → required; has default → optional |
| param `default` | Parameter default value | Carried over as-is |

```python
def send_message(channel: str, text: str, retries: int = 3) -> bool:
    """Send a message to a Slack channel."""
    ...
```

Introspects as:

```yaml
name: send_message
description: Send a message to a Slack channel.
params:
  channel:  (str, required)
  text:     (str, required)
  retries:  (int, default: 3)
```

## Overriding introspected fields

Any introspected field can be overridden in YAML. This is useful for renaming params, tightening descriptions, or hiding internal parameters with `override`. **Overridden param values are NEVER exposed to the LLM**

```yaml
tools:
  - fn: mypackage.api:call
    name: api-call
    description: Call the internal API with the given endpoint and payload.
    params:
      - name: endpoint
        type: str
        required: true
        description: API path, e.g. /users/list
      - name: api_key
        type: str
        override: ${INTERNAL_API_KEY}   # injected at load time, never exposed to LLM
```

See [Parameters](parameters.md) for the full param reference including overrides.

## Async functions

Async callables are fully supported. MCC awaits them automatically:

```python
async def fetch_data(url: str) -> dict:
    """Fetch JSON data from a URL."""
    ...
```

```yaml
tools:
  - fn: mypackage.http:fetch_data
```
