---
icon: lucide/terminal
---

# CLI Reference

MCC ships a management CLI for administering users, browsing tools, and running the MCP server.

```bash
mcc [OPTIONS] COMMAND [ARGS]...
```

## Global options

| Option | Description |
|--------|-------------|
| `-t`, `--tool` | Load a tool YAML file on startup (repeatable) |
| `-c`, `--config` | Load a config file into Dynaconf (repeatable) |
| `-e`, `--env` | Dynaconf environment to activate (e.g. `development`, `production`) |

The `--tool` flag loads additional tool files before executing any subcommand. Use it to test tools without adding them to `settings.local.yaml`:

```bash
mcc -t mytools.yaml tool list
mcc -t tools/a.yaml -t tools/b.yaml tool call my.tool arg=value
```

The `--config` flag injects additional Dynaconf config files, useful for overriding settings without editing `settings.local.yaml`:

```bash
mcc -c staging.yaml mcp serve
mcc -c prod.yaml -c secrets.yaml mcp serve -t http
```

The `--env` flag sets the active Dynaconf environment, enabling environment-layered config in your settings files:

```bash
mcc -e production mcp serve
mcc -e staging tool list
```

---

## `mcc user`

Manage users and their permissions.

### `add`

Create a new user.

```bash
mcc user add -u <username> [--email EMAIL] [-g GROUP ...] [-t TOOL ...]
```

| Option | Description |
|--------|-------------|
| `-u`, `--username` | GitHub username (required) |
| `-e`, `--email` | User's email address |
| `-g`, `--group` | Group to grant (repeatable) |
| `-t`, `--tool` | Tool key to grant (repeatable) |

```bash
mcc user add -u alice --email alice@example.com -g engineering
```

---

### `list`

List all users with their groups and tool grants.

```bash
mcc user list
```

---

### `remove`

Delete a user.

```bash
mcc user remove <username>
```

---

### `grant`

Grant a user group membership or an explicit tool permission.

```bash
mcc user grant <username> [-g GROUP ...] [-t TOOL ...]
```

At least one `-g` or `-t` is required. Both flags are repeatable.

```bash
mcc user grant alice -g engineering        # group membership
mcc user grant alice -g admin              # full admin access
mcc user grant alice -t admin.shell        # specific tool
mcc user grant alice -g data -g ml         # multiple groups at once
```

---

### `revoke`

Remove group membership or tool grants from a user.

```bash
mcc user revoke <username> [-g GROUP ...] [-t TOOL ...]
```

At least one `-g` or `-t` is required. Both flags are repeatable.

---

## `mcc tool`

Browse and call catalog tools.

### `list`

List all registered tools.

```bash
mcc tool list [-l]
```

| Option | Description |
|--------|-------------|
| `-l`, `--long` | Show full signatures instead of just keys |

---

### `info`

Print the full signature of a tool by key.

```bash
mcc tool info <tool-key>
```

```bash
mcc tool info admin.shell
```

---

### `call`

Invoke a tool by key and print the result.

```bash
mcc tool call <tool-key> [key=value ...] [--json JSON]
```

| Argument | Description |
|----------|-------------|
| `tool-key` | Exact tool key (e.g. `admin.shell`, `public.request`) |
| `key=value` | Parameters as positional `key=value` pairs (repeatable) |
| `--json` | Parameters as a JSON object string |

```bash
mcc tool call admin.auth.users.list_users
mcc tool call admin.shell command="ls -la"
mcc tool call my.tool name=foo count=3
mcc tool call my.tool --json '{"name": "foo", "count": 3}'
```

Output is syntax-highlighted JSON for dicts and lists, plain text otherwise.

---

## `mcc mcp`

Start the MCP server and install it in Claude clients.

### `serve`

Start the MCP server.

```bash
mcc mcp serve [-t stdio|http] [-h HOST] [-p PORT]
```

| Option | Default | Description |
|--------|---------|-------------|
| `-t`, `--transport` | `stdio` | Transport protocol (`stdio` or `http`) |
| `-h`, `--host` | `0.0.0.0` | Host to bind (HTTP only) |
| `-p`, `--port` | `8000` | Port to bind (HTTP only) |

```bash
mcc mcp serve                              # stdio (default, for Claude Desktop / Claude Code)
mcc mcp serve -t http                      # HTTP on 0.0.0.0:8000
mcc mcp serve -t http -p 9000
```

---

### `install`

Register MCC as an MCP server in a client's config. Most install subcommands mount the current project in editable mode so local changes are picked up immediately.

Common options available on all install subcommands:

| Option | Description |
|--------|-------------|
| `--env KEY=VALUE` | Set an environment variable (repeatable) |
| `--env-file FILE` | Load environment variables from a `.env` file |

#### `claude-code`

```bash
mcc mcp install claude-code [--env KEY=VALUE] [--env-file FILE]
```

```bash
mcc mcp install claude-code --env-file .env
```

#### `claude-desktop`

```bash
mcc mcp install claude-desktop [--env KEY=VALUE] [--env-file FILE]
```

```bash
mcc mcp install claude-desktop --env-file .env
```

#### `cursor`

```bash
mcc mcp install cursor [--env KEY=VALUE] [--env-file FILE]
```

```bash
mcc mcp install cursor --env-file .env
```

#### `gemini-cli`

```bash
mcc mcp install gemini-cli [--env KEY=VALUE] [--env-file FILE]
```

```bash
mcc mcp install gemini-cli --env-file .env
```

#### `goose`

```bash
mcc mcp install goose [--env KEY=VALUE] [--env-file FILE]
```

!!! note "Goose and env vars"
    Goose installs via a deeplink that does not carry environment variables. Use `mcc mcp install mcp-json` to generate a full config for manual installation if you need env vars set.


#### `mcp-json`

Print the MCP JSON config snippet — useful for manual installation or other clients.

```bash
mcc mcp install mcp-json [--env KEY=VALUE] [--env-file FILE] [--copy]
```

| Option | Description |
|--------|-------------|
| `--copy` | Copy output to clipboard instead of printing |

```bash
mcc mcp install mcp-json
mcc mcp install mcp-json --copy
```
