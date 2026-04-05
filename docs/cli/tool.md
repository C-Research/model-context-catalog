# mcc tool

Inspect and invoke tools from the command line.

## Commands

### `mcc tool list`

List all registered tools with their groups and descriptions.

```bash
mcc tool list
```

---

### `mcc tool call`

Invoke a tool by key and print the result.

```bash
mcc tool call <tool-key> [--params JSON]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `tool-key` | Exact tool key (e.g. `admin.shell`, `public.request`) |
| `--params` | JSON string of parameters |

**Examples:**

```bash
mcc tool call admin.shell --params '{"command": "ls -la"}'
mcc tool call public.request --params '{"url": "https://example.com"}'
mcc tool call admin.reload
```

Output is syntax-highlighted JSON.
