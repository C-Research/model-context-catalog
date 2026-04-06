# mcc mcp

Start the MCP server and install it in Claude clients.


## `serve`

Start the MCP server.

```bash
mcc mcp serve [-t stdio|http] [-h HOST] [-p PORT]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `-t`, `--transport` | `stdio` | Transport protocol (`stdio` or `http`) |
| `-h`, `--host` | `0.0.0.0` | Host to bind (HTTP only) |
| `-p`, `--port` | `8000` | Port to bind (HTTP only) |

**Examples:**

```bash
mcc mcp serve                              # stdio (default, for Claude Desktop / Claude Code)
mcc mcp serve -t http                      # HTTP on 0.0.0.0:8000
mcc mcp serve -t http -p 9000
```

---

## `install`

Register MCC as an MCP server in a client's config. All install commands mount
the current project in editable mode so local changes are picked up immediately.

Common options available on all install subcommands:

| Option | Description |
|--------|-------------|
| `--env KEY=VALUE` | Set an environment variable (repeatable) |
| `--env-file FILE` | Load environment variables from a `.env` file |

---

### `claude-code`

Install MCC in Claude Code.

```bash
mcc mcp install claude-code [--env KEY=VALUE] [--env-file FILE]
```

**Example:**

```bash
mcc mcp install claude-code --env-file .env
```

---

### `claude-desktop`

Install MCC in Claude Desktop.

```bash
mcc mcp install claude-desktop [--env KEY=VALUE] [--env-file FILE]
```

**Example:**

```bash
mcc mcp install claude-desktop --env-file .env
```

---

### `mcp-json`

Print the MCP JSON config snippet (useful for manual installation or other clients).

```bash
mcc mcp install mcp-json [--env KEY=VALUE] [--env-file FILE] [--copy]
```

**Options:**

| Option | Description |
|--------|-------------|
| `--copy` | Copy output to clipboard instead of printing |

**Example:**

```bash
mcc mcp install mcp-json
mcc mcp install mcp-json --copy
```
