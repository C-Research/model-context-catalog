# MCC — Model Context Catalog

An MCP server that exposes Python functions and shell commands as a permission-controlled tool catalog. Claude and other LLM clients discover and call tools through a unified `search` / `execute` interface, with RBAC and pluggable authentication built in.

---

## Features

- Serve multiple tools from one MCP by exposing Python functions or shell/exec commands
- Published catalog of tools for easy discoverability and llm execution
- Built in RBAC with user management and tool groups
- Multiple auth backends (dev unauthed, Github OAuth2, PAT)
- Optional contrib toolsets (utils and OSINT) loaded via `MCC_SETTINGS_FILES`
- CLI management of users and tools
- Async tool support

---

## How it works

Tools are defined in YAML files pointing at Python callables. MCC loads them, enforces per-user permissions, and serves them to any LLM via MCP.

```
Claude → search("deploy") → ["myteam.deploy - Deploys the app  execute(environment: str = 'dev')"]
Claude → execute("myteam.deploy", {"environment": "prod"})  →  result
```

---

## Quickstart


```bash
uv add model-context-catalog
```

**1. Configure auth** (`settings.local.yaml`):
```yaml
auth: dev-admin   # dev mode: no auth
```

**2. Add an admin user:**
```bash
mcc user add -u alice -e alice@example.com -g admin
```

**3. Run the server:**
```bash
python -m mcc.app
```

**4. Point your MCP client** at the HTTP endpoint.

---

## Defining Tools

Create a YAML file anywhere:

```yaml
group: myteam
tools:
  - fn: mypackage.mymodule:my_function     # required: dotted import path
    name: my-tool                          # optional: defaults to __name__
    description: "Does something useful"   # optional: defaults to __doc__
    params:                                # optional: introspected from signature
      - name: message
        type: str          # str | int | float | bool | list | dict
        required: true
      - name: flag
        type: bool
        override: true     # always injected at call time, hidden from callers
```

### Exec Tools (External Commands)

Run any command — Node, Go, shell scripts — as a catalog tool:

```yaml
tools:
  # Interpolation mode (default): params formatted into command string
  - name: grep
    exec: "grep -rn {pattern} {path}"
    params:
      - name: pattern
        type: str
        required: true
      - name: path
        type: str
        default: "."

  # Stdin mode: params sent as JSON on stdin
  - name: lint
    exec: "node tools/lint.js"
    stdin: true
    timeout: 30
    params:
      - name: file
        type: str
        required: true

  # With resource limits (unix only)
  - name: sandbox
    exec: "python3 untrusted.py"
    stdin: true
    timeout: 10
    limits:
      mem_mb: 256
      cpu_sec: 5
      fsize_mb: 50
      nofile: 128
```

Exec tools always return `(returncode, stdout, stderr)`. Params must be declared in YAML (no signature to introspect).

> **⚠ Security**: With `stdin: false` (the default), parameters are interpolated directly into the shell command. Do not expose exec tools with user-controlled params to untrusted callers without additional input validation.

Register it in `settings.local.yaml`:
```yaml
tools:
  - path/to/mytools.yaml
```

To load optional contrib toolsets, use `MCC_SETTINGS_FILES`:
```bash
# utils — HTTP, filesystem, shell, text, time, archives
MCC_SETTINGS_FILES=toolsets/contrib/settings.yaml

# OSINT — threat intel, corporate records, geolocation, and more
MCC_SETTINGS_FILES=toolsets/osint/settings.yaml

# both
MCC_SETTINGS_FILES=toolsets/contrib/settings.yaml;toolsets/osint/settings.yaml
```

---

## Authentication

Switch backends via `auth` in settings:

| Backend | When to use |
|---------|-------------|
| `dangerous` | Local dev — no auth, auto-selects first admin user |
| `github_pat` | Simple deployments — use a GitHub PAT for identity |
| `github_oauth` | Production — full OAuth2 flow via GitHub |

GitHub PAT config:
```yaml
default:
  auth: "github_pat"

  github_pat:
    token: "ghp_..."
```

GitHub OAuth config:
```yaml
default:
  auth: "github_oauth"

  github_oauth:
    client_id: "..."
    client_secret: "..."
    base_url: "https://your-server.example.com"
```

---

## User & Permission Management

```bash
mcc user add -u alice -e alice@example.com -g myteam
mcc user add -u bob -g admin
mcc user list
mcc user grant alice -g ops -t custom.tool
mcc user revoke alice -t custom.tool
mcc user remove alice
```

**Permission hierarchy** (first match wins):
1. Tool is in the `public` group → anyone can access
2. User is in the `admin` group → can access everything
3. User's groups include the tool's group → allowed
4. Tool key is in the user's explicit tool grants → allowed

---


## Documentation

- **[Getting Started](docs/getting-started/installation.md)** — installation, quickstart, configuration
- **[Tools](docs/tools/yaml-format.md)** — YAML format, Python tools, exec tools, parameters, resource limits
- **[Auth & Permissions](docs/auth/overview.md)** — backends, users, groups
- **[Contrib Toolsets](toolsets/docs/index.md)** — utils (HTTP, filesystem, shell, text, time, archives) and OSINT (threat intel, corporate records, geolocation, and more)

See [`openspec/project.md`](openspec/project.md) for a full architectural breakdown.
Inspiration [How to build an enterprise-grade MCP registry](https://www.infoworld.com/article/4145014/how-to-build-an-enterprise-grade-mcp-registry.html)