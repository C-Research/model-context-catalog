## Why

The MCP server currently only exposes two tools (`search` and `execute`) with auth and logging inlined. FastMCP provides resources, prompts, and middleware that would make the catalog richer for LLMs, clean up cross-cutting concerns, and give clients more ways to interact with tools.

## What Changes

- **Resources**: Expose the tool catalog as MCP resources so LLMs can read tool details into context without calling `search()`. `catalog://tools` lists accessible tools, `catalog://tools/{key}` returns a single tool's signature. `user://me` exposes current user identity, groups, and permissions.
- **Prompts**: Ship reusable prompt templates for common workflows — `find_and_run`, `explain_tool`, `debug_error` — so LLMs are effective out of the box.
- **Middleware**: Extract auth resolution, RBAC enforcement, and logging from `execute()`/`search()` into FastMCP middleware. Auth middleware resolves user and stashes in context. Logging middleware captures who called what. Add built-in `TimingMiddleware` for free perf metrics.

## Capabilities

### New Capabilities
- `mcp-resources`: MCP resource endpoints for catalog browsing and user identity
- `mcp-prompts`: Reusable prompt templates for tool discovery and execution workflows
- `mcp-middleware`: Auth, logging, and timing middleware using FastMCP's middleware pipeline

### Modified Capabilities
- `execute-tool`: Simplify `execute()` and `search()` by removing inline auth/logging (moved to middleware)

## Impact

- `mcc/app.py` — Add resource/prompt decorators, register middleware, simplify `execute()`/`search()`
- `mcc/middleware.py` — New module for auth and logging middleware classes
- Tests — New test files for resources, prompts, and middleware
