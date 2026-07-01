---
icon: lucide/key
---

# Environment Variables

There are two separate ways environment variables interact with MCC tools, and they operate at different times:

| Mechanism | Field | When | Purpose |
|-----------|-------|------|---------|
| YAML substitution | `${VAR}` / `$VAR` | Load time | Embed server config into YAML values |
| Subprocess environment | `env:`, `env_file:`, `env_passthrough:` | Call time | Control what the subprocess sees at runtime |
| Session store | `MCC_CTX` / `MCC_CTX_*` *(injected)* | Call time | Propagate the caller's identity and session vars into the subprocess |

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

Controls how much of the parent process environment the subprocess inherits as a base, on top of the always-present [env floor](#env-floor). Accepts a boolean or a list of glob patterns.

| Value | Subprocess base environment |
|-------|------------------------------|
| `false` *(default)* | The env floor only |
| `[ "GLOB", ... ]` | The env floor, plus parent variables whose names match any glob |
| `true` | A full copy of the current environment |

In all cases, `env_file:` is overlaid next and `env:` after that. The injected [session store](#session-store-mcc_ctx) (`MCC_CTX` for `fn:` tools, `MCC_CTX_*` for `exec:` tools) is applied **last** of all, so a tool's own `env:` can never spoof the caller's identity.

**`false` (default) — floor only.** The subprocess receives the env floor (`PATH`, `HOME`, etc.) plus whatever you explicitly declare. No secrets leak in:

```yaml
tools:
  - fn: mypackage.processor:run
    env:
      INPUT_PATH: /data/input
      OUTPUT_PATH: /data/output
    # subprocess sees the floor + INPUT_PATH + OUTPUT_PATH
```

**list — allowlist.** Each entry is a case-sensitive [`fnmatch`](https://docs.python.org/3/library/fnmatch.html) glob (`*`, `?`, `[seq]`) matched against parent variable **names**. Matching variables are merged over the floor. This is the precise, sudo-style way to expose exactly what a tool needs:

```yaml
tools:
  - fn: mypackage.deploy:push
    env_passthrough: ["AWS_*", "GIT_*"]
    # subprocess inherits the floor + every AWS_* and GIT_* var,
    # but NOT GITHUB_TOKEN, DATABASE_URL, or other secrets
```

Names are matched case-sensitively, so `"PATH"` matches `PATH` but `"path"` does not. An exact name (no wildcards) passes exactly that one variable. An empty list (`[]`) is equivalent to `false`.

**`true` — full environment (discouraged).** The subprocess starts from a full copy of the current environment, with `env:` / `env_file:` overlaid on top:

```yaml
tools:
  - fn: mypackage.deploy:push
    env:
      DEPLOY_ENV: production
    env_passthrough: true
    # subprocess inherits PATH, HOME, PYTHONPATH, credentials — everything
```

!!! warning "env_passthrough: true and secret leakage"
    With `env_passthrough: true` the subprocess receives every environment variable the MCC server process has — including API tokens, cloud credentials, and anything else that may be present. Prefer a glob allowlist (`env_passthrough: ["AWS_*"]`) to expose only what the tool needs.

#### Env floor

A fixed set of "machine works" variables is **always** exposed to every subprocess, regardless of `env_passthrough` — including `false`. A variable is only passed through if it is actually present in the server process environment. The default floor is:

```
PATH  HOME  USER  LOGNAME  TMPDIR  LANG  LC_ALL  TZ  TERM  SHELL
```

The floor contains no secrets. It is what lets `exec:`/`curl:` tools find binaries (`PATH`) and `fn:` tools import normally under default-deny. Configure it deployment-wide via `env_floor:` in settings (or `MCC_ENV_FLOOR`); there is no per-tool override and no way to drop below it.

---

## Session store (`MCC_CTX`)

Every tool call carries the **session store**: a single dictionary bundling the caller's identity with any mutable variables the session has stashed. This section covers how that dictionary is *propagated* into tool subprocesses. For the concept, the `get_session` / `set_session` tools, scope, and lifetime, see [Session Store](session.md).

The session store is propagated automatically on every `fn:` and `exec:` tool — there is nothing to declare in YAML — but the **shape differs by tool kind**:

- **`fn:` (Python) tools** receive the whole dictionary as one JSON env var, `MCC_CTX`, and may receive it as a typed `context` argument (see below).
- **`exec:` (shell) tools** receive each entry expanded into its own `MCC_CTX_<NAME>` env var (uppercased), stringified.

The dictionary always carries the [reserved identity keys](session.md#reserved-identity-keys) `user`, `email`, `groups`, and `tools`, alongside whatever the session set via `set_session`.

### `fn:` tools — the `MCC_CTX` blob and the `context` argument

A `fn:` subprocess always sees `MCC_CTX`, the JSON-encoded dictionary:

```python
import json, os

def report():
    ctx = json.loads(os.environ.get("MCC_CTX", "{}"))
    user = ctx.get("user")
    groups = ctx.get("groups", [])
    ...
```

More conveniently, **if your callable declares a parameter named `context`, MCC injects the parsed dictionary as that argument** — with real types preserved (lists stay lists, numbers stay numbers). The `context` parameter is hidden from the tool's public signature: the LLM never sees it and is never prompted for it.

```python
def report(target: str, context: dict) -> dict:
    # `target` is supplied by the caller; `context` is injected by MCC.
    return {"target": target, "called_by": context["user"]}
```

If the callable has no `context` parameter, nothing is injected — the blob is still present in the environment for tools that prefer to read it directly.

### `exec:` tools — `MCC_CTX_<NAME>` expansion

A shell tool can't take a Python argument, so each dictionary entry becomes its own env var named `MCC_CTX_<NAME>` (the key uppercased). Scalars are written raw; complex values (lists/objects) are JSON-encoded into the string. `exec:` tools do **not** receive the `MCC_CTX` blob.

For a user `alice` in groups `admin` and `osint` who has set `budget=1000`, the subprocess sees:

```
MCC_CTX_USER=alice
MCC_CTX_EMAIL=alice@example.com
MCC_CTX_GROUPS=["admin", "osint"]
MCC_CTX_BUDGET=1000
```

```yaml
tools:
  - name: whoami_echo
    exec: |
      echo "called by $MCC_CTX_USER"
      echo "groups json: $MCC_CTX_GROUPS"
```

### Semantics

- **Identity wins over `env:` and over stored values.** The context is merged **last** — after `env_passthrough`, `env_file:`, and `env:` — so a tool can't spoof the caller by declaring its own `MCC_CTX_USER`; and the identity keys are re-derived from the request on every call, so a stale or tampered stored blob can never impersonate or outlive a permission change.
- **`anonymous` identity.** An unauthenticated call still carries `user="anonymous"`; there is no separate "absent" signal.
- **No secrets.** Only identity and the variables the session itself set are propagated. The auth token is never exposed to the subprocess.

!!! note "Naming"
    The prefix is `MCC_CTX` / `MCC_CTX_` (not bare `MCC_`) to keep the context out of the `MCC_`-prefixed [settings namespace](../getting-started/configuration.md), which is read by dynaconf.

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

`PATH` is part of the default [env floor](#env-floor), so external binaries (`kubectl`, `git`, `curl`, …) are found out of the box even with `env_passthrough: false`. You only need to set `PATH` explicitly if your deployment has removed it from the floor, or to pin a specific search path:

```yaml
tools:
  # PATH comes from the floor; only the extra var is declared
  - name: deploy
    exec: kubectl apply -f {{ manifest | quote }}
    env:
      KUBECONFIG: /etc/deploy/kubeconfig

  # Pin an explicit PATH when you don't want the floor's value
  - name: deploy_pinned
    exec: kubectl apply -f {{ manifest | quote }}
    env:
      PATH: /usr/local/bin:/usr/bin:/bin
      KUBECONFIG: /etc/deploy/kubeconfig
```

---

## Python tools: environment and imports

Because `fn:` tools always execute in a subprocess, the subprocess must be able to import the callable's module. MCC always injects the tool's `cwd` into `PYTHONPATH`, and the [env floor](#env-floor) covers the OS basics, so the common case works without any env configuration — the same environment is used at load-time introspection and at call time.

In practice imports rarely need more: the target interpreter's installed packages and editable installs are discoverable without env vars. The cases where you need explicit `env:`/`env_file:` or an allowlist entry:

- Code that reads env vars **at import time** (e.g. a Django `settings` module that requires `DJANGO_SETTINGS_MODULE`)
- Modules that rely on an externally-set `PYTHONPATH` or `VIRTUAL_ENV` rather than installed as a package

Declare the specific vars you need, or allowlist them by glob:

```yaml
tools:
  # Explicit values — only what's needed
  - fn: mydjango.app:run_task
    env:
      DJANGO_SETTINGS_MODULE: mydjango.settings.production
      DATABASE_URL: postgres://localhost/prod

  # Allowlist a parent var the import relies on
  - fn: mypackage.app:run_task
    env_passthrough: ["VIRTUAL_ENV"]
```
