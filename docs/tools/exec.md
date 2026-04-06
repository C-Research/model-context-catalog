# Exec Tools

Any shell command can be wrapped as a catalog tool using the `exec:` field. No Python code required — just declare the command, describe the parameters, and MCC handles validation, interpolation, and execution.

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

Use `exec:` instead of `fn:`. The `name` field is required for exec tools (there's no callable to introspect).

## Return value

All exec tools return a tuple:

```python
(returncode: int, stdout: str, stderr: str)
```

- `returncode` is the called process' return code. A zero returncode means success. Non-zero means the command failed
- `stdout` text of standard output
- `stderr` text of standard error

## Templating

Exec commands are [Jinja2](https://jinja.palletsprojects.com/) templates. Parameters are available as template variables.

### The `| quote` filter

!!! warning "Quoting is your responsibility"
    No automatic quoting is applied. Every user-supplied value interpolated into the command should go through `quote`. If not quoted there is a possibility of shell injection exploits to expose secrets or do RCE.

    ```yaml
    # Unsafe:
    exec: grep {{ pattern }} {{ path }}

    # Safe:
    exec: grep {{ pattern | quote }} {{ path | quote }}
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

If a template references a variable that isn't provided, an `UndefinedError` is raised **before** the subprocess runs. There is no silent empty-string substitution.

### Environment variables

[EnvYAML](https://github.com/thesimj/envyaml) resolves `${VAR}` environment variable references at **load time**, before any Jinja rendering. The two compose cleanly:

```yaml
tools:
  - name: log_append
    exec: "cat {{ file | quote }} >> ${LOG_DIR}/out.txt"
    params:
      - name: file
        type: str
        required: true
```

At load time, `${LOG_DIR}` is replaced with the environment variable value. At call time, Jinja renders `{{ file | quote }}`. They never interfere.



## Stdin mode

Set `stdin: true` to send all validated parameters as a JSON object on stdin instead of interpolating into the command string. Useful for tools that read structured input:

```yaml
tools:
  - name: python
    exec: >
      python {% if verbose %}-vvv{% endif %} -c 'import sys, json; print(json.load(sys.stdin)["source"])'
    stdin: true
    params:
      - name: source
        type: str
        required: true
      - name: verbose
        type: bool
        default: false
```

When `stdin: true`, the Jinja template is still rendered (for the command itself), but params are delivered via stdin as a JSON blob.

## Timeout

Set a maximum runtime in seconds:

```yaml
tools:
  - name: slow_job
    exec: python -c 'import time; time.sleep(99999)'
    timeout: 30
```

On timeout, the process is killed and the tool returns `(-1, "", "timeout after 30s")`.

## Resource limits

On Unix, constrain subprocess resource usage:

```yaml
tools:
  - name: sandbox
    exec: python {{ script | quote }}
    limits:
      mem_mb: 256      # max memory (RLIMIT_AS)
      cpu_sec: 10      # max CPU time (RLIMIT_CPU)
      fsize_mb: 50     # max file write size (RLIMIT_FSIZE)
      nofile: 64       # max open file descriptors
    params:
      - name: script
        type: str
        required: true
```

