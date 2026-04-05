## 1. Middleware

- [x] 1.1 Create `mcc/middleware.py` with `AuthMiddleware` class — resolves user via `get_current_user()` on every request, stashes on context or contextvar
- [x] 1.2 Add `LoggingMiddleware` class — uses `logging.getLogger("mcc.middleware")` to inherit project logging config; hooks `on_call_tool` to log username, tool key, params, and timing
- [x] 1.3 Register `AuthMiddleware`, `LoggingMiddleware`, and FastMCP's `TimingMiddleware` on the mcp server in `app.py`
- [x] 1.4 Remove inline `get_current_user()` calls and manual logging from `execute()` and `search()` — read user from middleware context instead
- [x] 1.5 Test auth middleware resolves user for authenticated and anonymous requests
- [x] 1.6 Test logging middleware logs tool executions

## 2. Resources

- [x] 2.1 Add `catalog://tools` resource — returns `loader.list_all()` filtered by current user's access
- [x] 2.2 Add `catalog://tools/{key}` resource template — returns single tool signature if accessible, "not found" otherwise
- [x] 2.3 Add `user://me` resource — returns current user's username, email, groups, and tool grants (or anonymous identity)
- [x] 2.4 Test catalog resource returns only accessible tools
- [x] 2.5 Test tool resource template returns signature for accessible tool and "not found" for inaccessible/unknown
- [x] 2.6 Test user resource returns identity for authenticated and anonymous users

## 3. Prompts

- [x] 3.1 Add `find_and_run(task)` prompt — returns message template guiding LLM to search and execute
- [x] 3.2 Add `explain_tool(key)` prompt — returns message template asking LLM to describe a tool
- [x] 3.3 Add `debug_error(key, error)` prompt — returns message template asking LLM to diagnose a failure
- [x] 3.4 Test all three prompts return expected message content
