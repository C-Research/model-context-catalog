# mcc tool

Browse and call catalog tools.


## `list`

List all registered tools.

```bash
mcc tool list [-l]
```

**Options:**

| Option | Description |
|--------|-------------|
| `-l`, `--long` | Show full signatures instead of just keys |

---

## `info`

Print the full signature of a tool by key.

```bash
mcc tool info <tool-key>
```

**Example:**

```bash
mcc tool info admin.shell
```

---

## `call`

Invoke a tool by key and print the result.

```bash
mcc tool call <tool-key> [key=value ...] [--json JSON]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `tool-key` | Exact tool key (e.g. `admin.shell`, `public.request`) |
| `key=value` | Parameters as positional `key=value` pairs (repeatable) |
| `--json` | Parameters as a JSON object string |

**Examples:**

```bash
mcc tool call admin.auth.users.list_users
mcc tool call admin.shell command="ls -la"
mcc tool call my.tool name=foo count=3
mcc tool call my.tool --json '{"name": "foo", "count": 3}'
```

Output is syntax-highlighted JSON for dicts and lists, plain text otherwise.
