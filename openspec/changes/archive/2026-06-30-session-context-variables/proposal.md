## Why

Today the caller's identity is propagated into tool subprocesses as a fixed set of
`MCC_CTX_USER / EMAIL / GROUPS / TOOLS` environment variables (see `mcc/context.py`).
This is one-directional and immutable: a tool can read who is calling, but there is
no shared, mutable scratch space that survives across calls within a session. LLM
workflows frequently want to stash a value once (a target host, a budget, a selected
record) and have later tool calls pick it up without re-passing it every time.

This change generalizes the per-call identity vars into a **per-session, per-user
context dictionary** that the LLM can read and write through two new catalog tools,
and that every tool execution receives as input. Identity becomes just a set of
reserved keys inside that one dictionary — "one var to rule them all."

## What Changes

- **New MCP tools** `get_context(name)` and `set_context(name, value)` exposed
  in-process alongside `search` / `execute` / `whoami`.
- **New session-scoped context store** backed by Elasticsearch via FastMCP's
  `session_state_store` hook (`key_value` `ElasticsearchStore`, reusing the existing
  ES client wiring from `mcc/db.py`).
- **Scope** is `(session_id, username)`: the effective storage key is
  `{session_id}:{username}:context`. Anonymous callers use `username="anonymous"`
  and rely on `session_id` for isolation.
- **Identity folds into the context dict.** The dict always carries reserved keys
  `user`, `email`, `groups`, `tools`. `set_context` refuses to write reserved keys.
- **fn (Python) tools** receive the whole dict as a single `MCC_CTX` JSON env var,
  which `pyrunner` loads and injects into the callable as a `context` kwarg — but
  **only if the callable declares a `context` parameter**. The injected `context`
  param is hidden from the tool's public signature (shadowed, like `override` params).
- **exec (shell) tools** receive the dict **expanded** into one env var per entry:
  `MCC_CTX_<NAME>=value`. Values are stringified (scalars raw, complex JSON-encoded).
  exec tools do **not** receive the `MCC_CTX` blob.
- **BREAKING:** the existing discrete `MCC_CTX_USER / EMAIL / GROUPS / TOOLS`
  identity-only env injection is removed and replaced by the mechanism above. exec
  tools still see `MCC_CTX_USER` etc. — but now as expanded entries of the unified
  dict, not as a bespoke identity path.

## Capabilities

### New Capabilities

- `session-context`: a per-(session, user) mutable context dictionary, the
  `get_context` / `set_context` tools, the ES-backed session state store, reserved
  identity keys, and the differentiated propagation into fn vs exec tools.

### Modified Capabilities

- None formally specced. The current `MCC_CTX_*` caller-identity propagation was
  shipped without an OpenSpec change, so this proposal introduces the first spec for
  that behavior (superseding it) under the new `session-context` capability.

## Impact

- `mcc/context.py`: `user_env()` replaced by context-dict assembly + reserved-key
  logic; `ENV_PREFIX` semantics change.
- `mcc/exec.py`: `_proc_extra` / env builders updated to emit `MCC_CTX` (fn) vs
  `MCC_CTX_<NAME>` expansion (exec).
- `mcc/pyrunner.py`: load `MCC_CTX`, inject `context` kwarg when the callable
  declares it.
- `mcc/models.py`: introspection/validation marks a declared `context` param as
  hidden/injected so it never reaches the LLM schema or elicitation.
- `mcc/app.py`: register `get_context` / `set_context`; wire `session_state_store`
  onto the `FastMCP` instance; `execute` reads the context snapshot.
- `docs/tools/env-vars.md`: rewrite the "Caller identity" section.
- Dependencies: `py-key-value-aio` (already installed; `ElasticsearchStore`).
- No new settings required for the default 24h TTL; ES connection reuses
  `ELASTICSEARCH_URL`.
