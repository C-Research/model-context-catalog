# MCP Interface

MCC exposes two tools to LLM clients — `search` and `execute` — plus a set of resources and prompts for catalog browsing and guided workflows.

## search

```
search(query, min_score?)
```

Finds tools by natural language using hybrid keyword + semantic search over the catalog. Only tools the current user has access to are returned.

Each result is a **signature block** — a compact markdown description of a tool — prefixed with its relevance score in brackets:

```
[9.14]
## admin.shell
groups: admin
params:
  - command (str, required): Shell command to run
returns: (returncode: int, stdout: str, stderr: str)

Run a shell command and return its output.

[8.71]
## admin.auth.users.list_users
groups: admin, auth, users
returns: list

List all users in the catalog.
```

Each signature includes:

- **Tool key** — the heading (`## admin.shell`). Pass this to `execute`.
- **groups** — which groups can access the tool.
- **params** — name, type, required/optional, and description for each parameter.
- **returns** — the return type. Exec tools return `stdout` as a string on success, or `(code, stdout, stderr)` on error.
- **Description** — what the tool does.

**Scores are relative** — compare them to each other, not to a fixed scale. A large gap between top and bottom scores means the lower results are probably not relevant. Use `min_score` to filter after an initial search to observe the score distribution. Typical useful scores range from 1.0 to 15.0 depending on query specificity.

To narrow by group, include the group name in your query (e.g. `"admin shell command"`).

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | `str` | Natural language description of what you're looking for |
| `min_score` | `float` (optional) | Exclude results below this score |

## execute

```
execute(name, params?)
```

Runs a tool by its exact key. The key is shown in `search` results. Parameters must match the tool's declared names and types; required parameters must be included.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Exact tool key (e.g. `admin.shell`, `public.request`) |
| `params` | `dict` (optional) | Parameter name → value. Omit for tools with no required parameters |

Returns the tool's output, a validation error if params don't match, or `Unauthorized` if the current user doesn't have access.

## Resources

Readable catalog views available via MCP resource URIs:

| URI | Description |
|-----|-------------|
| `catalog://tools` | All tools the current user can access |
| `catalog://tools/{key}` | A single tool's signature by key |
| `user://me` | Current user's identity, groups, and tool grants |

## Prompts

Reusable workflow templates:

| Name | Parameters | Description |
|------|------------|-------------|
| `find_and_run` | `task` | Search for a tool matching a task description and execute it |
| `explain_tool` | `key` | Explain what a tool does, its parameters, and when to use it |
| `debug_error` | `key`, `error` | Diagnose a tool execution error and suggest fixes |
