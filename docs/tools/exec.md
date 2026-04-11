# Exec Tools

Any shell command can be wrapped as a catalog tool using the `exec:` field. No Python code required — declare the command, describe the parameters, and MCC handles validation, interpolation, and execution.

## Basic structure

```yaml
tools:
  - name: word_count
    exec: wc -l {{ file | quote }}
    description: Count lines in a file
    params:
      - name: file
        type: str
        required: true
```

Use `exec:` instead of `fn:`. The `name` field is required for exec tools (there is no callable to introspect it from).

---

## How it works

When an exec tool is called:

1. **Validate** — MCC validates parameters against the declared `params`.
2. **Render** — The command string is rendered as a Jinja2 template with the validated parameter values.
3. **Execute** — The rendered command is run via `/bin/sh -c <cmd>` as an async subprocess.
4. **Return** — stdout is returned on success; `(returncode, stdout, stderr)` on failure.

### Return value

On **success** (exit code 0) the tool returns a string — the subprocess stdout.

On **failure** (non-zero exit code) the tool returns a tuple:

```python
(returncode: int, stdout: str, stderr: str)
```

```yaml
# returns "hello\n" on success
- name: greet
  exec: echo hello

# returns (-1, "", "timeout after 5s") if killed
- name: slow
  exec: sleep 999
  timeout: 5
```

---

## Templating

Exec commands are [Jinja2](https://jinja.palletsprojects.com/) templates. Validated parameter values are available as template variables.

### The `| quote` filter

!!! warning "Quoting is your responsibility"
    No automatic quoting is applied. Every user-supplied value interpolated into the command should go through `| quote`. Without it, values containing spaces, semicolons, or shell metacharacters can break the command or enable injection.

    ```yaml
    # Safe:
    exec: grep {{ pattern | quote }} {{ path | quote }}
    
    # Unsafe:
    exec: grep {{ pattern }} {{ path }}
    ```

The `| quote` filter applies [`shlex.quote`](https://docs.python.org/3/library/shlex.html#shlex.quote) to safely escape values for shell interpolation.

**Scalar values:**

```jinja
{{ "hello world" | quote }}  →  'hello world'
{{ "foo" | quote }}          →  foo
{{ "a;b" | quote }}          →  'a;b'
```

**List values** — each element is quoted and joined with spaces:

```jinja
{{ ["a.txt", "b c.txt"] | quote }}  →  a.txt 'b c.txt'
{{ [] | quote }}                    →  (empty string)
```

### Conditional blocks

Use `{% if %}` to include optional flags:

```yaml
tools:
  - name: search
    exec: grep {% if recursive %}-r {% endif %}{{ pattern | quote }} {{ path | quote }}
    params:
      - name: pattern
        type: str
        required: true
      - name: path
        type: str
        required: true
      - name: recursive
        type: bool
        default: false
```

### Missing variables

If a template references a variable that was not provided, an `UndefinedError` is raised **before** the subprocess runs. There is no silent empty-string substitution.

### `${VAR}` — load-time substitution

[EnvYAML](https://github.com/thesimj/envyaml) resolves `${VAR}` references at **load time**, before any Jinja rendering. Use this to embed server-side configuration into the command:

```yaml
tools:
  - name: log_append
    exec: "cat {{ file | quote }} >> ${LOG_DIR}/out.txt"
    params:
      - name: file
        type: str
        required: true
```

At load time `${LOG_DIR}` is substituted from the environment. At call time Jinja renders `{{ file | quote }}`. They never interfere.

---

## Stdin mode

Set `stdin: true` to deliver all validated parameters as a JSON object on stdin instead of interpolating them into the command string. The Jinja template is still rendered for the command itself, but params arrive via stdin as a JSON blob.

Useful for tools that read structured input or when parameters contain characters that are awkward to quote:

```yaml
tools:
  - name: process_json
    exec: python -c 'import sys, json; json.load(sys.stdin)["key"]'
    stdin: true
    params:
      - name: key
        type: str
        required: true

  - name: python_eval
    exec: >
      python {% if verbose %}-v {% endif %}-c
      'import sys, json; exec(json.load(sys.stdin)["source"])'
    stdin: true
    params:
      - name: source
        type: str
        required: true
      - name: verbose
        type: bool
        default: false
```

Stdin and Jinja templating compose: the command is rendered from params at call time, then params are also sent as `{"key": "value", ...}` on stdin.

---

## curl shorthand

The `curl:` field is a convenience wrapper for HTTP tools. It automatically prepends `curl -s -o -`, keeping tool definitions focused on the URL and any extra flags.

```yaml
tools:
  - name: geolocate
    curl: "http://ip-api.com/json/{{ query }}"
```

This is equivalent to:

```yaml
  - name: geolocate
    exec: curl -s -o - "http://ip-api.com/json/{{ query }}"
```

### With request body

Add `stdin: true` to send all parameters as a JSON body via `--json @-`:

```yaml
tools:
  - name: search
    curl: https://api.example.com/search
    stdin: true
    params:
      - name: q
        type: str
        required: true
```

`stdin: true` causes MCC to pipe `{"q": "..."}` to curl's stdin, and appends `--json @-` to the command — which sets `Content-Type: application/json` and `Accept: application/json` automatically.

### Extra curl flags

Put anything that would normally follow `curl -s -o -` directly in the `curl:` value — headers, method flags, URL templates:

```yaml
tools:
  - name: private_api
    curl: "-H 'Authorization: Bearer ${API_TOKEN}' https://api.example.com/{{ resource }}"
    params:
      - name: resource
        type: str
        required: true
```

All Jinja2 templating, `${VAR}` load-time substitution, and runtime options (`timeout`, `env`, `env_file`, etc.) work exactly as they do for `exec:` tools.

---

## Runtime options

All common runtime fields (`cwd`, `env`, `env_file`, `env_passthrough`, `timeout`, `limits`) are documented in [YAML Tool Format → Runtime options](yaml-format.md#runtime-options). Below are `exec`-specific notes and examples.

### Working directory

```yaml
tools:
  - name: build
    exec: make all
    cwd: /srv/myproject
    timeout: 300
```

### Environment variables

Exec tools have two separate env mechanisms that operate at different times. See [Environment Variables → Exec tools](env-vars.md#exec-tools-two-mechanisms) for the full reference including load-time `${VAR}` substitution, call-time `env:`/`env_file:`, and `PATH` handling with `env_passthrough: false`.

### Timeout and resource limits

`timeout:` sets a wall-clock deadline in seconds; `limits:` caps CPU, memory, and other OS resources. See [Resource Limits](limits.md) for the full reference.

```yaml
tools:
  - name: render
    exec: ffmpeg -i {{ input | quote }} {{ output | quote }}
    timeout: 600
    limits:
      mem_mb: 2048
      cpu_sec: 300
    params:
      - name: input
        type: str
      - name: output
        type: str
```
