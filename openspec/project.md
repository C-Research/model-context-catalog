# MCC — Model Context Catalog: Project Overview

MCC is an MCP (Model Context Protocol) server that acts as a permission-controlled catalog of Python tools. It lets you expose arbitrary Python functions to Claude and other LLM clients through a unified `search` / `execute` interface, with authentication and RBAC built in.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   MCP Client (Claude)               │
└───────────────────────┬─────────────────────────────┘
                        │ HTTP (MCP protocol)
┌───────────────────────▼─────────────────────────────┐
│                    app.py (FastMCP)                  │
│                                                      │
│   search(query, group)    execute(name, params)      │
└──────────┬────────────────────────┬─────────────────┘
           │                        │
    ┌──────▼──────┐         ┌───────▼───────┐
    │  loader.py  │         │  auth/util.py │
    │  (Loader)   │         │  can_access() │
    └──────┬──────┘         └───────┬───────┘
           │                        │
    ┌──────▼──────┐         ┌───────▼───────┐
    │  models.py  │         │  auth/db.py   │
    │  ToolModel  │         │  (TinyDB)     │
    └──────┬──────┘         └───────────────┘
           │
    ┌──────▼──────┐
    │  YAML files │  ← mcc/tools/, contrib/, user paths
    └─────────────┘
```

---

## Key Modules

### `mcc/app.py`
FastMCP server entry point. Exposes two MCP tools:
- `search(query, group=None)` — returns signatures of tools the current user can access
- `execute(name, params=None)` — runs a tool by key, validates params, checks permissions

Bootstraps the loader on startup and wires in the auth backend.

### `mcc/loader.py`
`Loader` (a dict subclass) reads YAML tool definition files and registers `ToolModel` instances by key (`group.name` or `name`). Supports recursive directory loading, uniqueness enforcement, and hot `reload()`.

`load_file(path)` handles the YAML → list of ToolModels conversion.

### `mcc/models.py`
Two Pydantic models:

**`ParamModel`** — one parameter on a tool:
| Field | Purpose |
|-------|---------|
| `name` | Argument name |
| `type` | One of: str, int, float, bool, list, dict |
| `required` | Whether the caller must supply it |
| `default` | Default value if not required |
| `description` | Shown in signatures |
| `override` | Always injects this value at call time; hidden from callers |

**`ToolModel`** — a complete tool entry:
- `fn` — dotted import path to the callable (`module.path:attr` or `module.path.attr`)
- `params` — auto-introspected from signature if not provided in YAML
- `name` / `description` — auto-populated from `__name__` / `__doc__` if omitted
- `call(**kwargs)` — validates caller args, injects overrides, executes (sync or async)
- `signature` — formatted string shown to the LLM
- `param_model` — dynamically created Pydantic model for input validation
- `can_access(user)` — delegates to auth layer

### `mcc/settings.py`
Dynaconf-backed config. Priority order (highest → lowest):
1. `MCC_*` environment variables
2. `settings.local.toml`
3. `mcc/settings.toml`

Key knobs: `auth`, `contrib`, `tools` (list of extra YAML paths), `users_db`, `logging`.

### `mcc/auth/`

| Module | Role |
|--------|------|
| `db.py` | TinyDB CRUD for users: username, email, groups[], tools[] |
| `util.py` | `can_access()` permission logic; `get_current_user()` token → user resolution |
| `backend.py` | Selects and proxies the active auth backend |
| `github_oauth.py` | OAuth2 via FastMCP's GitHubProvider |
| `github_pat.py` | PAT-based identity (queries GitHub API) |
| `dangerous.py` | No-auth dev mode — auto-selects first admin user |

**Permission hierarchy** (first match wins):
1. Tool in `public` group → always allowed
2. User in `admin` group → always allowed
3. User's `groups` contains the tool's group → allowed
4. Tool key in user's `tools` list → allowed
5. Otherwise → denied

### `mcc/contrib/`
Optional built-in tools, enabled via `contrib = true`:

| Tool | Group | What it does |
|------|-------|-------------|
| `public.request` | public | HTTP requests via httpx (responsible/browser UA toggle) |
| `admin.shell` | admin | Arbitrary shell command execution |

### `mcc/cli.py`
Click CLI (`mcc` entry point) for user and permission management:
```
mcc add-user / list-users / remove-user
mcc grant / revoke
```

---

## Tool Loading Pipeline

```
YAML file
  └─ group: mygroup
     tools:
       - fn: mymodule:my_fn         ← required
         name: my-tool              ← optional, defaults to __name__
         description: "..."         ← optional, defaults to __doc__
         params:                    ← optional, introspected from signature
           - name: arg
             type: str
             required: true
           - name: flag
             type: bool
             override: true         ← always injected, hidden from callers

         ↓  load_file()
         ↓  ToolModel (Pydantic validates, resolves callable)
         ↓  Loader.register("mygroup.my-tool", tool)

execute("mygroup.my-tool", {"arg": "hello"})
  ↓  can_access(user, tool)
  ↓  param_model(arg="hello")      ← validates caller-supplied params
  ↓  inject overrides              ← flag=True added silently
  ↓  my_fn(arg="hello", flag=True)
```

---

## Data Flow: Auth

```
MCP request (with token)
  └─ backend.get_user_context()    ← extracts token claims
  └─ util.get_current_user()       ← resolves email/login → DB user dict
  └─ can_access(user, tool)        ← checks groups + explicit grants
```

---

## Adding Tools

1. Create a YAML file:
```yaml
group: myteam
tools:
  - fn: mypackage.mymodule:my_function
```

2. Register in `settings.local.toml`:
```toml
[default]
tools = ["path/to/mytools.yaml"]
```

3. Grant users access:
```bash
mcc grant alice -g myteam
```

That's it. The loader picks it up on next startup (or `admin.reload`).
