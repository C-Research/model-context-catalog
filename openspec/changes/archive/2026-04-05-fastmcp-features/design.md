## Context

The MCP server uses FastMCP but only leverages `@mcp.tool()` and auth. Auth checks and logging are duplicated inside `search()` and `execute()`. FastMCP provides resources, prompts, and middleware that would improve separation of concerns and give LLM clients richer interaction.

## Goals / Non-Goals

**Goals:**
- Expose catalog and user info as MCP resources
- Ship prompt templates for common workflows
- Extract auth and logging into middleware
- Simplify `execute()` and `search()` handlers

**Non-Goals:**
- Changing the underlying auth system
- Modifying the tool loader or ToolModel
- Adding caching middleware (future consideration)

## Decisions

### 1. Resources use access-filtered tool lists

`catalog://tools` returns only tools the current user can access, not the full catalog. This matches `search()` behavior and avoids leaking tool names the user shouldn't see. `catalog://tools/{key}` returns 404 (or empty) if the user can't access that tool.

`user://me` returns the user's identity, groups, and tool grants. This replaces the need for a separate groups resource.

### 2. Auth middleware resolves user, doesn't block

The auth middleware resolves the current user via `get_current_user()` and stashes the result on the FastMCP `Context`. It does NOT block requests — handlers decide what to do with the user (filter results in `search`, reject in `execute`). This matches the existing behavior where `search()` filters rather than rejects.

The middleware uses `on_message` to resolve the user for all request types (tools, resources, prompts).

### 3. Logging middleware inherits project logging config

Logging middleware uses `logging.getLogger("mcc.middleware")` which inherits level, formatter, and handlers from the `mcc` logger configured via `settings.yaml` / `logging.config.dictConfig`. No custom log setup — it just works with whatever the user has configured (DEBUG in dev, INFO+verbose in prod, etc.).

The middleware hooks `on_call_tool` specifically to log tool executions with user, tool key, params, and timing. This replaces the manual `logger.info` in `execute()`.

### 4. Prompts are simple string returns

Prompt functions return plain strings (auto-converted to user messages by FastMCP). No need for `Message` or `PromptResult` — the templates are simple enough.

### 5. All new code in `mcc/app.py` and `mcc/middleware.py`

Resources and prompts are registered in `app.py` alongside existing tools. Middleware classes live in a new `mcc/middleware.py` module and are added to the server in `app.py`.

## Risks / Trade-offs

- **Middleware ordering** → Auth must run before logging so the user is available. FastMCP processes middleware in registration order.
- **Context stashing** → FastMCP's `Context` object may not support arbitrary attributes. Fallback: use a module-level contextvar for the resolved user (already how `get_user_context` works).
- **Resource performance** → `catalog://tools` iterates all tools and filters. For large catalogs this could be slow. Acceptable for now; caching middleware is a future option.
