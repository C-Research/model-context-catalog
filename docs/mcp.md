---
icon: lucide/plug
---

# MCP Interface

MCC exposes two tools to LLM clients — `search` and `execute` — plus a set of resources and prompts for catalog browsing and guided workflows.

## search

```
search(query, min_score?)
```

Finds tools by natural language using hybrid keyword + semantic search over the catalog. Only tools the current user has access to are returned.

Each result is a **signature block** — a compact markdown description of a tool — prefixed with its relevance score in brackets:

```markdown
[8.02]
## academic.semantic_scholar_search (query:str, limit:int=10) -> str
`query` — Search query string.
`limit` — Number of results to return. Default 10, max 100.
Search the Semantic Scholar academic graph for papers by keyword.
Returns JSON with titles, authors, year, abstract, citation counts, and open-access PDF links.
```

Each signature includes:

- **Relevance score** - the `[..]` numerical heading is the result's relevancy score
- **Tool key** — the heading (`## academic.semantic_scholar_search `). Pass this to `execute`. Key also declares which groups can access the tool.
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
execute(key, params?)
```

Runs a tool by its exact key. The key is shown in `search` results. Parameters must match the tool's declared names and types; required parameters must be included.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | `str` | Exact tool key (e.g. `admin.shell`, `public.request`) |
| `params` | `dict` (optional) | Parameter name → value. Omit for tools with no required parameters |

Returns the tool's output, a validation error if params don't match, or `Unauthorized` if the current user doesn't have access.

## Prompts

Reusable workflow templates:

| Name | Parameters | Description |
|------|------------|-------------|
| `find_and_run` | `task` | Search for a tool matching a task description and execute it |
| `explain_tool` | `key` | Explain what a tool does, its parameters, and when to use it |
| `debug_error` | `key`, `error` | Diagnose a tool execution error and suggest fixes |

## describe_tools

```
describe_tools(groups?)
```

Lists all tools accessible to the current user, returning only the tool key and description. Useful for browsing the catalog without the overhead of full signatures. Use `search()` to get parameter details before calling `execute()`.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `groups` | `list[str]` (optional) | If provided, only tools belonging to **all** of the specified groups are returned |

Each entry in the response uses the format:

```
## admin.shell
Run a shell command and return its output.

## public.request
Make an HTTP request and return the response.
```
