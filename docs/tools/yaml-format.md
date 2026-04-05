# YAML Tool Format

Tools are defined in YAML files. Each file declares a list of tools, optionally scoped to one or more groups.

## Basic structure

```yaml
groups: [mygroup]          # optional — defaults to [public]
tools:
  - fn: mymodule:my_fn     # required — dotted import path to the callable
    name: my-tool          # optional — defaults to function __name__
    description: "..."     # optional — defaults to function __doc__
    params:                # optional — introspected from signature if omitted
      - name: arg
        type: str
        required: true
```

## `fn` — the callable

Points at any importable Python callable using either colon or dot notation:

```yaml
fn: mypackage.mymodule:my_function   # colon separator (preferred)
fn: mypackage.mymodule.my_function   # dot separator also works
```

## `groups`

Controls which users can access the tools in this file. Can be set at the file level or overridden per tool:

```yaml
groups: [engineering]     # all tools in this file default to [engineering]
tools:
  - fn: mymodule:tool_a   # inherits [engineering]
  - fn: mymodule:tool_b
    groups: [admin]       # overrides to [admin] for this tool only
```

Omit `groups` entirely to default to `[public]` (accessible to all users).

## `name` and `description`

Both are optional and auto-populated from the function:

```yaml
tools:
  - fn: mymodule:send_email
    # name defaults to "send_email"
    # description defaults to send_email.__doc__
```

## Tool key

Each registered tool gets a key derived from its groups and name:

```
key = ".".join(sorted(groups) + [name])
```

Examples:

| groups | name | key |
|--------|------|-----|
| `[public]` | `greet` | `public.greet` |
| `[admin]` | `shell` | `admin.shell` |
| `[admin, ops]` | `deploy` | `admin.ops.deploy` |

Use the key with `execute()`.

## Loading multiple files

Register additional YAML files in `settings.local.toml`:

```toml
[default]
tools = [
  "mytools.yaml",
  "path/to/more_tools.yaml",
]
```

MCC also recursively loads all `*.yaml` files from any directory path you provide.
