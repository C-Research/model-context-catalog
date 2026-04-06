# Environment Variables

There are two separate ways environment variables interact with MCC tools, and they operate at different times:

| Mechanism | Field | When | Purpose |
|-----------|-------|------|---------|
| YAML substitution | `${VAR}` / `$VAR` | Load time | Embed server config into YAML values |
| Subprocess environment | `env:`, `env_file:`, `env_passthrough:` | Call time | Control what the subprocess sees at runtime |

They are independent and can be combined. The sections below cover each in detail.

---

## Load-time substitution (`${VAR}`)

Any value in a YAML tool file can reference an environment variable using `$VAR_NAME` or `${VAR_NAME}` syntax. MCC uses [EnvYAML](https://github.com/thesimj/envyaml) to resolve these at load time — before any tool is ever called.

```yaml
groups: [internal]
tools:
  - fn: mypackage.api:call
    description: Calls the internal API
    params:
      - name: api_key
        type: str
        override: $INTERNAL_API_KEY      # substituted at load time

      - name: base_url
        type: str
        override: ${API_BASE_URL}
```

At load time MCC reads the values from the server's environment:

```bash
export INTERNAL_API_KEY=secret123
export API_BASE_URL=https://api.internal.example.com
```

### Behavior when a variable is unset

If a referenced variable is not set, MCC leaves the literal string as-is (e.g. `$INTERNAL_API_KEY`). No error is raised at load time.

!!! tip "Use load-time substitution for overrides"
    Load-time substitution is the right tool for injecting secrets into `override:` params. The value is baked in at load time and never exposed to the LLM.

---

## Runtime environment

The fields below control what environment variables the subprocess receives when a tool runs. They apply to both `fn:` and `exec:` tools.

### `env:`

A dict of key/value pairs to set in the subprocess environment. Values are strings.

```yaml
tools:
  - fn: mypackage.db:query
    env:
      DATABASE_URL: postgres://localhost/mydb
      LOG_LEVEL: warning
```

### `env_file:`

Path to a file in [dotenv format](https://pypi.org/project/python-dotenv/). Variables are loaded from the file into the subprocess environment.

```yaml
tools:
  - fn: mypackage.api:call
    env_file: /etc/myapp/secrets.env
```

Dotenv format:

```dotenv
API_KEY=secret123
DATABASE_URL=postgres://db.internal/prod
TIMEOUT=30
# lines starting with # are comments
```

### Combining `env:` and `env_file:`

Both can be set on the same tool. `env:` values take priority and override any same-named entries from `env_file:`:

```yaml
tools:
  - fn: mypackage.api:call
    env_file: /etc/myapp/secrets.env    # API_KEY=..., LOG_LEVEL=info
    env:
      LOG_LEVEL: debug                  # overrides the value from the file
```

### `env_passthrough:`

Controls whether the subprocess inherits the parent process environment as a base.

| Value | Subprocess environment |
|-------|------------------------|
| `false` *(default)* | Only variables from `env:` and `env_file:` — nothing else |
| `true` | Full copy of the current environment, with `env:` / `env_file:` overlaid on top |

**`false` (default) — isolated.** The subprocess only receives what you explicitly declare. Nothing from the server process leaks in:

```yaml
tools:
  - fn: mypackage.processor:run
    env:
      INPUT_PATH: /data/input
      OUTPUT_PATH: /data/output
    # subprocess sees ONLY INPUT_PATH and OUTPUT_PATH
```

**`true` — additive.** The subprocess starts from a full copy of the current environment, with your `env:` / `env_file:` entries overlaid on top. Use this when you want to extend the environment rather than replace it:

```yaml
tools:
  - fn: mypackage.deploy:push
    env:
      DEPLOY_ENV: production
    env_passthrough: true
    # subprocess inherits PATH, HOME, PYTHONPATH, credentials, etc.
    # DEPLOY_ENV is added on top
```

!!! warning "env_passthrough: true and secret leakage"
    With `env_passthrough: true` the subprocess receives every environment variable the MCC server process has — including API tokens, cloud credentials, and anything else that may be present. Use `false` (the default) unless you have a specific reason to pass the full environment through.

---

## Exec tools: two mechanisms

`exec:` tools have access to both load-time substitution and the runtime environment fields. They operate at different stages and serve different purposes:

| Mechanism | When | Use for |
|-----------|------|---------|
| `${VAR}` in YAML | Load time | Baking a fixed server-side value into the command string itself |
| `env:` / `env_file:` | Call time | Variables the subprocess reads at runtime |

```yaml
tools:
  - name: pg_query
    exec: psql -U myapp -d mydb -c {{ sql | quote }}
    env:
      PGPASSWORD: ${DB_PASSWORD}    # ${} resolved at load time; PGPASSWORD set at call time
    params:
      - name: sql
        type: str
        required: true
```

`${DB_PASSWORD}` is read from the server's environment when MCC starts and baked into the tool definition as the value of `PGPASSWORD`. At call time, the subprocess receives `PGPASSWORD` with that baked-in value.

### `PATH` and shell commands

With `env_passthrough: false` (the default), exec subprocess environments do not have `PATH`. Shell builtins (`echo`, `cd`, `test`, etc.) work fine — they are part of `/bin/sh` itself. External binaries require either their full path or an explicit `PATH` entry:

```yaml
tools:
  # Option A: explicit PATH, nothing else leaks
  - name: deploy
    exec: kubectl apply -f {{ manifest | quote }}
    env:
      PATH: /usr/local/bin:/usr/bin:/bin
      KUBECONFIG: /etc/deploy/kubeconfig

  # Option B: full passthrough when you need everything
  - name: deploy
    exec: kubectl apply -f {{ manifest | quote }}
    env_passthrough: true
```

---

## Python tools: environment and imports

Because `fn:` tools always execute in a subprocess, the subprocess must be able to import the callable's module. With `env_passthrough: false` (the default), the subprocess does not inherit `PYTHONPATH` or other env vars from the server process.

In practice this is rarely a problem: the target interpreter's installed packages and editable installs are discoverable without env vars. The cases where `env_passthrough: true` (or explicit env entries) are needed:

- Code that reads env vars **at import time** (e.g. a Django `settings` module that requires `DJANGO_SETTINGS_MODULE`)
- Modules that rely on `PYTHONPATH` being set externally rather than installed as a package

Prefer declaring the specific vars you need over passing the entire environment:

```yaml
tools:
  # Explicit — only what's needed
  - fn: mydjango.app:run_task
    env:
      DJANGO_SETTINGS_MODULE: mydjango.settings.production
      DATABASE_URL: postgres://localhost/prod

  # Full passthrough — convenient but broad
  - fn: mydjango.app:run_task
    env_passthrough: true
```
