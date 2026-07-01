## 1. Session state store

- [x] 1.1 Add `session_index_prefix: "mcc-ctx"` to `mcc/settings.yaml` (alongside `user_index`/`tool_index`/`key_index`)
- [x] 1.2 Add `ElasticsearchStore` construction in `mcc/app.py`, reusing `mcc/db.py::_client_kwargs` for the `AsyncElasticsearch` client (`index_prefix=settings.SESSION_INDEX_PREFIX`)
- [x] 1.3 Pass it as `FastMCP(session_state_store=...)` on the existing `mcp` instance
- [x] 1.4 Confirm the store writes only to `{prefix}-fastmcp_state` and leaves `mcc-users`/`mcc-tools`/`mcc-keys` untouched
- [x] 1.5 Confirm default TTL (24h) is acceptable with no new setting

## 2. Context assembly + scoping (mcc/context.py)

- [x] 2.1 Add reserved-key constant `{user, email, groups, tools}` and the slug pattern `^[a-z_][a-z0-9_]*$`
- [x] 2.2 Implement `identity_fields(user) -> dict` producing the reserved keys from `UserModel` (anonymous → `user="anonymous"`, others omitted/empty as appropriate)
- [x] 2.3 Implement the scope-key helper: state key = `f"{username}:context"` (FastMCP prefixes `session_id`)
- [x] 2.4 Implement `assemble_context(stored_vars, user) -> dict` = reserved identity merged over stored mutable vars (identity wins)
- [x] 2.5 Implement env builders: `ctx_blob_env(dict) -> {"MCC_CTX": json}` (fn) and `ctx_expanded_env(dict) -> {"MCC_CTX_<NAME>": str}` (exec), scalars raw / complex JSON-encoded
- [x] 2.6 Remove the old `user_env()` identity-only path (keep `current_user_var` — it stays authoritative)
- [x] 2.7 Re-derive identity from `current_user_var` each request and merge over stored vars (identity wins); never trust blob identity

## 3. get_context / set_context tools (mcc/app.py)

- [x] 3.1 `set_context(ctx, name, value)` — validate slug, reject reserved keys, read blob → mutate field → write blob via `ctx.set_state(f"{username}:context", blob)`
- [x] 3.2 `get_context(ctx, name)` — read blob via `ctx.get_state`, return field or `null`; reserved keys resolve from assembled identity
- [x] 3.3 Resolve `username` from `current_user_var` (anonymous fallback) inside both tools
- [x] 3.4 Write clear docstrings (LLM-facing) for both tools

## 4. Snapshot injection in execute (mcc/app.py)

- [x] 4.1 In `execute`, read stored vars for `(session, user)` and call `assemble_context`
- [x] 4.2 Thread the assembled dict to `tool.call(...)` so the exec layer can build the right env (fn blob vs exec expansion)

## 5. Subprocess env wiring (mcc/exec.py)

- [x] 5.1 `_proc_extra` (or callers) emit `MCC_CTX` for `fn:` tools and `MCC_CTX_<NAME>` expansion for `exec:` tools
- [x] 5.2 Ensure context env is merged LAST (cannot be spoofed by tool `env:`)
- [x] 5.3 Keep `MCC_SKIP_AUTOLOAD` / `PYTHONPATH` behavior intact

## 6. pyrunner context kwarg (mcc/pyrunner.py)

- [x] 6.1 In `execute`, parse `MCC_CTX` from env (tolerate absent/blank)
- [x] 6.2 Inspect the resolved callable's signature; if it declares `context`, pass the parsed dict as that kwarg
- [x] 6.3 Keep `pyrunner` stdlib-only (no mcc imports)

## 7. Shadow the context param (mcc/models.py)

- [x] 7.1 During introspection, detect a `context` param on `fn:` tools and mark it injected/hidden (exclude from `visible_params`, like `override`)
- [x] 7.2 Ensure it is never elicited (`_elicit_missing`) and never validated as caller-supplied

## 8. Tests

- [x] 8.1 `set_context` / `get_context` round-trip for authed and anonymous callers
- [x] 8.2 Session isolation (two sessions same user) and user isolation (same session id, different user)
- [x] 8.3 Reserved-key rejection on `set`; slug validation rejects bad names
- [x] 8.4 fn tool: `MCC_CTX` present, `context` kwarg injected only when declared, hidden from signature
- [x] 8.5 exec tool: `MCC_CTX_<NAME>` expansion (scalar raw, complex JSON), no `MCC_CTX` blob
- [x] 8.6 Identity-spoof test: tool `env: {MCC_CTX_USER: attacker}` cannot override caller
- [x] 8.7 Missing key returns `null`; typed values survive round-trip for fn tools

## 9. Docs

- [x] 9.1 Rewrite the "Caller identity (`MCC_CTX_*`)" section of `docs/tools/env-vars.md` for the unified dict, `MCC_CTX` blob vs expansion, and the `context` kwarg
- [x] 9.2 Document `get_context` / `set_context`, scoping, reserved keys, slug rule, and TTL

## 10. Verify

- [x] 10.1 Run pytest, ruff, pyright (per AGENTS.md) and ensure green
