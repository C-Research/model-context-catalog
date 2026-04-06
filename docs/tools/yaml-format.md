# YAML Tool Format

Tools are defined in YAML files. Each file declares a list of tools, optionally scoped to one or more groups.

!!! tip "Be explicit"
    Fill out as much detail in the tool and parameter descriptions as all info is sent to the LLM for context on how to use it.

## Basic structure

```yaml
groups: [mygroup]       # optional — defaults to [public]
tools:
  - fn: mymodule:my_fn  # python callable (fn: or exec: required, not both)
    name: my-tool       # optional for fn, required for exec
    description: "..."  # optional for fn, recommended for exec
    params:             # optional for fn (introspected), required for exec
      - name: arg
        type: str
        required: true
```

Each tool uses either `fn` to call a Python callable or `exec` to run a shell command — see [Python Tools](python.md) and [Exec Tools](exec.md) respectively.

## `groups`

Controls which users can access the tools in this file. Can be set at the file level and overridden per tool:

```yaml
groups: [engineering]     # all tools in this file default to [engineering]
tools:
  - fn: mymodule:tool_a   # inherits [engineering]
  - fn: mymodule:tool_b
    groups: [admin]       # overrides to [admin] for this tool only
```

Omit `groups` entirely to default to `[public]` (accessible to all users).

## `name` and `description`

For `fn` tools both fields are optional — MCC introspects them from the callable. For `exec` tools, `name` is required and `description` should be set manually since there's no callable to inspect.

```yaml
tools:
  - fn: mymodule:send_email     # name → "send_email", description → __doc__
  - name: compress              # exec tools must declare name explicitly
    exec: "gzip {{ file | quote }}"
    description: Compress a file with gzip
```

## `params`

Params define what the tool accepts. For `fn` tools they're introspected automatically. For `exec` tools they must be declared explicitly.

```yaml
params:
  - name: message
    type: str
    required: true
    description: The message to send
  - name: retries
    type: int
    default: 3
    description: Number of retry attempts
```

See [Parameters](parameters.md) for types, defaults, and overrides.

## Tool key

Each tool gets a key derived from its groups and name. `public` and `admin` sort to the front:

| groups | name | key |
|--------|------|-----|
| `[public]` | `greet` | `public.greet` |
| `[admin]` | `shell` | `admin.shell` |
| `[admin, ops]` | `deploy` | `admin.ops.deploy` |

Use the key with `execute()`.

## Loading multiple files

Register YAML files or directories in `settings.local.yaml`:

```yaml
tools:
  - mytools.yaml
  - path/to/more_tools.yaml
  - path/to/tools_dir        # loads all *.yaml files in this directory
```
