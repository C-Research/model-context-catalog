---
icon: lucide/code
---

# Exec Tool Templates

Exec tools use [Jinja2](https://jinja.palletsprojects.com/) for command templating. Parameters are available as template variables, and the `| quote` filter handles shell-safe quoting.

## Basic usage

```yaml
tools:
  - name: greet
    exec: "echo {{ name | quote }}"
    params:
      - name: name
        type: str
        required: true
```

When called with `name="hello world"`, this runs `echo 'hello world'`.

## The `| quote` filter

The `| quote` filter applies [`shlex.quote`](https://docs.python.org/3/library/shlex.html#shlex.quote) to safely escape values for shell interpolation.

**Scalar values** — the value is quoted as a single shell word:

```
{{ "hello world" | quote }}  →  'hello world'
{{ "foo" | quote }}          →  foo
{{ "a;b" | quote }}          →  'a;b'
```

**List values** — each element is quoted and joined with spaces:

```
{{ ["a.txt", "b c.txt"] | quote }}  →  a.txt 'b c.txt'
{{ [] | quote }}                    →  (empty string)
```

This makes it easy to pass a list of file paths or arguments:

```yaml
tools:
  - name: word_count
    exec: "wc -l {{ files | quote }}"
    params:
      - name: files
        type: list
        required: true
```

## Conditional blocks

Use `{% if %}` to include optional flags:

```yaml
tools:
  - name: search
    exec: "grep {% if recursive %}-r {% endif %}{{ pattern | quote }} {{ path | quote }}"
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

## Missing variables

If a template references a variable that isn't provided, an `UndefinedError` is raised **before** the subprocess runs. There is no silent empty-string substitution.

```yaml
exec: "echo {{ message | quote }}"
# Calling without `message` → UndefinedError immediately
```

## Environment variables and Jinja

[EnvYAML](https://github.com/thesimj/envyaml) resolves `${VAR}` environment variable references at **load time**, before any Jinja rendering. The two mechanisms compose cleanly:

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

## Security note

!!! warning "Quoting is your responsibility"
    Unlike the old format-string approach, **no automatic quoting is applied**. Every parameter interpolated into a shell command should go through `| quote` unless you have a specific reason not to (e.g., passing a pre-validated flag string).

    Omitting `| quote` on user-supplied input is a **shell injection risk**.

    ```yaml
    # Unsafe — don't do this with user input:
    exec: "grep {{ pattern }} {{ path }}"

    # Safe:
    exec: "grep {{ pattern | quote }} {{ path | quote }}"
    ```
