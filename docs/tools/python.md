---
icon: simple/python
---

# Python Tools

Python tools wrap any importable callable — a function, method, class, or `async` awaitable. MCC introspects the callable at load time to populate `name`, `description`, and `params` automatically, then executes it in a subprocess at call time.



!!! warning "MCP compatibility constraints"
    Because parameters are delivered to the callable as JSON kwargs from an LLM client, all callables must follow these rules:

    **No `*args`.** Variadic positional arguments cannot be represented in MCP tool schemas and are silently skipped during introspection. Every input the LLM needs to supply must be a named keyword argument.

    **All parameters must be JSON-serializable types.** Accepted types are `str`, `int`, `float`, `bool`, `list`, and `dict`. Class instances, custom objects, and other non-serializable types cannot be passed across the subprocess boundary and will fail at call time.

    **Return values must also be JSON-serializable.** The callable's return value is serialized with `json.dumps` before being sent back. Complex objects (dataclasses, ORM models, etc.) should be converted to dicts or lists before returning.

    ```python
    # Good — plain types in, plain types out
    def search(query: str, limit: int = 10) -> list[dict]:
        ...

    # Bad — *args can't be expressed in an MCP schema
    def merge(*sources: str) -> str:
        ...

    # Bad — MyModel instance can't cross the subprocess boundary
    def process(record: MyModel) -> MyModel:
        ...
    ```

## Defining a tool

Write a Python function (or point at one that already exists):

```python
# mypackage/utils.py
def greet(name: str) -> str:
    """Say hello to someone."""
    return f"Hi {name}"
```

Then reference it in your tool spec:

```yaml
tools:
  - fn: mypackage.utils:greet
```

That's the minimum. Name, description, and parameter types are all inferred from the function.

## `fn` syntax

Use colon notation to separate the module path from the attribute:

```yaml
fn: mypackage.mymodule:my_function        # preferred
fn: mypackage.mymodule.my_function        # dot notation also works
fn: mypackage.mymodule:MyClass.my_method  # nested attribute access
```

The module is imported with `importlib.import_module`, then each attribute after the colon (or the final dot segment) is resolved with `getattr`. Any importable Python object works — including stdlib:

```yaml
- name: regex_search
  fn: re:findall
  params:
    - name: pattern
      type: str
    - name: string
      type: str
```

---

## How it works

Every `fn` tool runs through two subprocess phases: **introspect** at load time and **exec** at call time. Both phases use `pyrunner.py`, a stdlib-only script that runs inside the target interpreter.

### Introspect phase (load time)

When MCC loads a YAML file it batches all `fn` entries that share the same Python interpreter into a single subprocess call:

```
python mcc/pyrunner.py introspect fn_path [fn_path ...]
```

`pyrunner.py` resolves and inspects each callable, then prints a JSON array to stdout — one entry per `fn_path`:

```json
[
  {
    "fn_path": "mypackage.utils:greet",
    "name": "greet",
    "doc": "Say hello to someone.",
    "params": [{"name": "name", "type": "str", "required": true, "default": null, "description": ""}],
    "return_type": "str"
  }
]
```

Introspection runs in two internal phases to surface errors clearly:

1. **Resolve** — `importlib.import_module` + `getattr` for each `fn_path`. Import errors are caught immediately, before any inspection work begins.
2. **Inspect** — `inspect.signature` and `inspect.getdoc` on each successfully resolved callable.

Each `fn_path` can fail independently without affecting others in the same batch. Failures include the full traceback so you know exactly what went wrong:

```json
{
  "fn_path": "mypackage.broken:tool",
  "error": "Traceback (most recent call last):\n  ...\nModuleNotFoundError: No module named 'mypackage'"
}
```

After introspection, MCC injects `name`, `description`, `params`, and `return_type` into the tool entry before constructing the `ToolModel`. The ToolModel skips its own per-tool subprocess if `params` is already populated.

**One subprocess per interpreter group.** If a YAML file has ten `fn` tools all using the default interpreter, MCC runs one `pyrunner.py introspect` call with all ten paths — not ten separate processes.

### Exec phase (call time)

When the tool is called:

```
python mcc/pyrunner.py exec fn_path
```

`pyrunner.py` reads a JSON blob of `kwargs` from stdin, resolves the callable, calls it (awaiting if async), and prints the JSON-encoded result to stdout:

```
stdin:  {"name": "Alice"}
stdout: "Hi Alice"
```

On success the tool returns the JSON-decoded result. On failure (non-zero exit) it returns `(returncode, stdout, stderr)`.

---

## Introspection field mapping

When a `fn` tool loads, MCC inspects the callable to fill in any missing fields:

!!! tip "Be explicit"
    It is always better to specify values in the tool spec to tailor to the LLM audience. Docstrings are for devs, descriptions are for LLMs.

| Field | Source | Notes |
|-------|--------|-------|
| `name` | `callable.__name__` | Override in YAML to change the catalog key |
| `description` | `inspect.getdoc(callable)` | Full docstring — sent to the LLM, so quality matters |
| `params` | `inspect.signature(callable)` | One entry per argument; `*args` and `**kwargs` are skipped |
| param `type` | Parameter annotation | Maps to `str`, `int`, `float`, `bool`, `list`, `dict`. Unannotated → `str` |
| param `required` | Presence of a default value | No default → required; has default → optional |
| param `default` | Parameter default value | Carried over as-is |
| `return_type` | Return annotation | Stored internally; shown in the tool signature |

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
returns: bool
```

## Overriding introspected fields

Any introspected field can be overridden in YAML:

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
        override: ${INTERNAL_API_KEY}   # injected at call time, never exposed to LLM
```

If `params` are declared explicitly in YAML, introspection is skipped entirely for that tool — the batch subprocess does not include it. This is also the fastest load path for tools where you know the signature won't change.

See [Parameters](parameters.md) for the full param reference including overrides.

## Async functions

Async callables are fully supported. `pyrunner.py` detects `asyncio.iscoroutinefunction` and runs the callable with `asyncio.run`:

```python
async def fetch_data(url: str) -> dict:
    """Fetch JSON data from a URL."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()
```

```yaml
tools:
  - fn: mypackage.http:fetch_data
```

---

## `python` — custom interpreter

By default MCC uses `sys.executable` (the interpreter running the MCC server) for all `fn` tools. Set `python:` to use a different interpreter:

```yaml
tools:
  - fn: mypackage.ml:predict
    python: /opt/ml-env/bin/python   # isolated venv with GPU libraries

  - fn: legacy.module:process
    python: /usr/bin/python3.9       # pinned Python version
```

Both the introspect subprocess and the exec subprocess use this interpreter. The path is resolved with `shutil.which` at load time — an invalid path raises immediately.

!!! tip "When to use `python:`"
    Use a custom interpreter when a tool's dependencies are not available in the MCC server's venv, or when you need a specific Python version. All other runtime behavior (`cwd`, `env`, `timeout`, etc.) works identically regardless of which interpreter is chosen.

---

## Runtime options

All common runtime fields (`cwd`, `env`, `env_file`, `env_passthrough`, `timeout`) are documented in [YAML Tool Format → Runtime options](yaml-format.md#runtime-options). Resource limits (`limits:`) are covered in [Resource Limits](limits.md). Below are `fn`-specific notes and examples.

### Subprocess environment and imports

Because `fn` tools run in a subprocess, the subprocess must be able to import the callable's module. See [Environment Variables → Python tools](env-vars.md#python-tools-environment-and-imports) for details on when `env_passthrough` matters for imports and how to declare only the variables you need.

### Working directory

```yaml
tools:
  - fn: mypackage.reports:generate
    cwd: /data/reports
    timeout: 300
```
