---
icon: lucide/file-text
---

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
    example: "..."      # optional — shown to the LLM as a usage example
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

## `name`, `description`, and `example`

For `fn` tools `name` and `description` are optional — MCC introspects them from the callable. For `exec` tools, `name` is required and `description` should be set manually since there's no callable to inspect.

`example` is optional for all tool types. Use it to give the LLM a concrete usage example shown directly in the tool signature.

!!! tip "Description and example directly affect LLM behavior"
    The tool signature is the only information the LLM has about what a tool does and when to use it. A missing or vague description causes the LLM to misuse the tool or skip it entirely. A good `description` explains the tool's purpose and when to reach for it; a good `example` shows a realistic invocation so the LLM can pattern-match against it.

```yaml
tools:
  - fn: mymodule:send_email     # name → "send_email", description → __doc__
  - name: compress              # exec tools must declare name explicitly
    exec: "gzip {{ file | quote }}"
    description: Compress a file with gzip
    example: "compress file=/var/log/app.log"
```

## `params`

Params define what the tool accepts. For `fn` tools they're introspected automatically. For `exec` tools they must be declared explicitly.

```yaml
params:
  - name: message
    type: str
    required: true
    description: The message to send
    example: "Hello, world!"
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

---

## Runtime options

The following fields apply to both `fn` and `exec` tools. They control the subprocess environment and execution constraints. Tool-specific options (`python:` for fn, `stdin:` for exec) are covered in their respective pages.

### Quick reference

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `cwd` | `str` | inherit | Working directory for the subprocess |
| `timeout` | `int` | none | Kill subprocess after N seconds |
| `env` | `dict` | `{}` | Explicit environment variables |
| `env_file` | `str` | none | Path to a `.env` file to source |
| `env_passthrough` | `bool` | `false` | Inherit the parent process environment |
| `limits` | `dict` | none | Unix resource limits (memory, CPU, etc.) |
| `transform` | `str` or `list[str]` | none | Shell pipeline to filter output before returning to the LLM |

---

### `cwd`

Set the working directory for the subprocess. Defaults to the MCC server's working directory.

```yaml
tools:
  - name: build
    exec: make all
    cwd: /srv/myproject

  - fn: mypackage.jobs:run
    cwd: /data/workspace
```

Useful when a tool reads relative paths or relies on a specific project root.

---

### `timeout`

Kill the subprocess after N seconds. Without it, long-running tools run indefinitely.

```yaml
tools:
  - name: report
    exec: python generate_report.py
    timeout: 120    # 2 minutes

  - fn: mypackage.jobs:run_analysis
    timeout: 30
```

On timeout the process is killed and the tool returns `(-1, "", "timeout after Ns")`.

---

### `env`, `env_file`, and `env_passthrough`

Control what environment variables the subprocess receives. See [Environment Variables](env-vars.md) for the full reference — including `env:` key/value pairs, `env_file:` dotenv files, combining them, and the `env_passthrough` flag that controls whether the subprocess inherits the parent environment.

---

### `limits`

Unix only. Cap CPU time, memory, file sizes, and open file descriptors via `setrlimit`. See [Resource Limits](limits.md) for a full reference of each field, what it measures, and how violations are reported.

```yaml
tools:
  - name: sandbox
    exec: python {{ script | quote }}
    limits:
      mem_mb: 256      # max virtual memory
      cpu_sec: 10      # max CPU time in seconds
      fsize_mb: 50     # max file write size
      nofile: 64       # max open file descriptors
    params:
      - name: script
        type: str
        required: true
```

---

### `transform`

Pipe tool output through a shell command before it's returned to the LLM. Use this to strip noise from large HTML, XML, or JSON responses so less content lands in the LLM's context window.

```yaml
tools:
  # single command
  - name: fetch-article
    curl: "https://example.com/{{ slug }}"
    transform: "pup 'article p text{}'"

  # multi-step pipeline (list is joined with |)
  - name: search
    curl: "https://api.example.com/search?q={{ query }}"
    transform:
      - "jq -r '.hits[].title'"
      - "head -c 4000"
```

The transform value is Jinja-templated with the same kwargs as the main command:

```yaml
tools:
  - name: extract
    curl: "https://example.com/{{ path }}"
    transform: "jq -r '.{{ field }}'"
    params:
      - name: path
        type: str
        required: true
      - name: field
        type: str
        default: data
```

Works with both `exec`/`curl` tools and `fn` tools. If the tool call fails, the transform is skipped and the error is returned unchanged. The transform shares the tool's `timeout` budget.
