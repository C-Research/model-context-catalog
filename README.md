# MCC — Model Context Catalog

An MCP server that exposes Python functions as a permission-controlled tool catalog. Claude and other LLM clients discover and call tools through a unified `search` / `execute` interface, with RBAC and pluggable authentication built in.

---

## Features

- Serve multiple tools from one mcp by exposing plain python functions
- Published catalog of tools for easy discoverability and llm execution
- Built in RBAC with user management and tool groups
- Multiple auth backends (dev unauthed, Github OAuth2, PAT)
- Optional contrib tools for admin and public users
- CLI management of users and tools
- Async tool support

---

## How it works

Tools are defined in YAML files pointing at Python callables. MCC loads them, enforces per-user permissions, and serves them to any LLM via MCP.

```
Claude → search("deploy") → ["myteam.deploy - Deploys the app  execute(...)"]
Claude → execute("myteam.deploy", {"environment": "prod"})  →  result
```

---

## Quickstart


```bash
uv add model-context-catalog
```

**1. Configure auth and extras** (`settings.local.toml`):
```toml
[default]
auth = "dangerous"   # dev mode: auto-uses first admin user
contrib = true       # enable built-in HTTP and shell tools
```

**2. Add an admin user:**
```bash
mcc add-user -u alice -e alice@example.com -g admin
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

Register it in `settings.local.toml`:
```toml
[default]
tools = ["path/to/mytools.yaml"]
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
```toml
[default]
auth = "github_pat"

[default.github_pat]
token = "ghp_..."
```

GitHub OAuth config:
```toml
[default]
auth = "github_oauth"

[default.github_oauth]
client_id = "..."
client_secret = "..."
base_url = "https://your-server.example.com"
```

---

## User & Permission Management

```bash
mcc add-user -u alice -e alice@example.com -g myteam
mcc add-user -u bob -g admin
mcc list-users
mcc grant alice -g ops -t custom.tool
mcc revoke alice -t custom.tool
mcc remove-user alice
```

**Permission hierarchy** (first match wins):
1. Tool is in the `public` group → anyone can access
2. User is in the `admin` group → can access everything
3. User's groups include the tool's group → allowed
4. Tool key is in the user's explicit tool grants → allowed

---


See [`openspec/project.md`](openspec/project.md) for a full architectural breakdown.
Inspiration [How to build an enterprise-grade MCP registry](https://www.infoworld.com/article/4145014/how-to-build-an-enterprise-grade-mcp-registry.html)