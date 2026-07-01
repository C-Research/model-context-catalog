## Context

MCC propagates caller identity into tool subprocesses as fixed `MCC_CTX_*` env vars
(`mcc/context.py::user_env`). It is read-only and per-call. We want a mutable,
session-scoped key/value bag the LLM can drive, with identity as reserved keys
inside it, propagated differently to Python vs shell tools.

FastMCP 3.2 already provides the primitives, so we do not roll our own session layer:

- `ctx.session_id` — stable per MCP session (from the `mcp-session-id` header for
  HTTP, a generated UUID otherwise).
- `ctx.set_state(key, value)` / `ctx.get_state(key)` — a session-scoped state store.
  Keys are auto-prefixed with `session_id` (`_make_state_key` → `f"{session_id}:{key}"`),
  so one session structurally cannot read another's keys.
- `FastMCP(session_state_store=...)` — pluggable `AsyncKeyValue` backend; defaults to
  in-memory `MemoryStore`.

`py-key-value-aio` (installed) ships `key_value.aio.stores.elasticsearch.ElasticsearchStore`,
which accepts an existing `AsyncElasticsearch` client — the same one `mcc/db.py`
builds from `ELASTICSEARCH_URL`.

## Goals / Non-Goals

**Goals**
- `get_context(name)` / `set_context(name, value)` MCP tools.
- Per-`(session, user)` isolation; anonymous supported via `username="anonymous"`.
- Identity (`user/email/groups/tools`) lives as reserved keys in the one dict.
- fn tools get the full dict as `MCC_CTX` JSON → injected `context` kwarg (only when
  declared); exec tools get `MCC_CTX_<NAME>` expansion.
- ES-backed store for multi-replica safety; reuse the existing ES client.

**Non-Goals**
- `context_list` / `context_delete` / `clear` — out of scope for this change.
- Durability beyond the session: state is ephemeral (TTL-bounded), not a user profile.
- Cross-session sharing for one user: by design two sessions are separate buckets.
- Back-compat with the old discrete `MCC_CTX_*` identity injection — removed.

## Decisions

### 1. Two tools, not one action-dispatched tool

`get_context(name)` and `set_context(name, value)` as separate catalog tools rather
than `context_var(action, name, value?)`. With a dispatched tool, `value` is required
in `set` mode and meaningless in `get` mode — a conditional validity the LLM cannot
read off the schema. Separate tools keep each schema self-describing: every parameter
present is always required. Cost is one extra catalog entry.

### 2. Single blob per (session, user), mutated field-wise

The entire context is stored under one state key, `context`, as a JSON object. The
effective ES key is `{session_id}:{username}:context` (FastMCP prefixes `session_id`;
we compose `username` into the key we pass). `set_context` does read-blob →
mutate-field → write-blob; `get_context` reads the blob and returns one field;
`execute` reads the blob once to build the snapshot. This avoids maintaining a
separate name-index and gives `execute` a single read.

**Alternative**: one state key per variable. Rejected — `execute` would need to
enumerate keys to assemble the dict, and the store's key listing is awkward/uneven
across backends.

### 3. Scope = (session_id, username)

Key composition: `set_state(f"{username}:context", ...)` → stored as
`{session_id}:{username}:context`. This binds context to **both** the connection and
the identity:
- Two tabs of one user → different `session_id` → separate buckets (no races).
- Even if two clients collided on `session_id`, distinct usernames never share a bucket.
- Anonymous: `username="anonymous"` is a constant label; `session_id` still separates
  distinct anonymous clients. Same trust assumption already accepted for authed
  sessions.

### 4. Identity as reserved keys; set() refuses them

The dict always contains `user`, `email`, `groups`, `tools`, populated from the
authenticated `UserModel` at assembly time. `set_context` rejects these names (model A:
flat namespace + reserved list) so a tool/LLM cannot spoof identity by writing
`set_context("user", "admin")`. The slug validator blocks the exotic cases; the
reserved list is small and stable.

**Alternative**: namespaced dict (`{identity:{...}, vars:{...}}`, model B). Rejected
for now — flat namespace matches the "`MCC_CTX_<NAME>` for everything" propagation and
needs no second prefix. Revisit if identity fields grow.

### 5. fn tools: `MCC_CTX` JSON blob → injected `context` kwarg

A single env var `MCC_CTX` carries the JSON-encoded dict. `pyrunner` loads it and, if
the resolved callable declares a `context` parameter, passes the parsed dict as that
kwarg. If the callable has no `context` param, nothing is injected (the blob is still
present in the env for tools that prefer to read it directly).

The `context` param is **shadowed**: at introspection it is recognized and excluded
from `visible_params`, so it never appears in the LLM-facing signature and is never
elicited — mirroring how `override` params are hidden today (`hidden_params`).

fn tools get real **typed** values (int/list/dict survive), because the transport is
JSON, not env-string.

### 6. exec tools: `MCC_CTX_<NAME>` expansion, stringified

Shell tools cannot take a Python kwarg, so each dict entry becomes its own env var:
`MCC_CTX_<UPPER_NAME>=value`. Scalars (str/int/float/bool) are written raw
(`MCC_CTX_BUDGET=1000`); complex values (dict/list) are JSON-encoded into the string.
exec tools do **not** receive the `MCC_CTX` blob. Because identity is in the dict,
exec tools still see `MCC_CTX_USER`, `MCC_CTX_GROUPS`, etc. — now as expanded entries,
not a bespoke path. We inject as strings and accept the typing loss for shell.

### 7. Name slug rule

`set_context` validates `name` against `^[a-z_][a-z0-9_]*$`. Lowercase, uppercased
only when forming the env suffix. One rule keeps a name simultaneously valid as a JSON
key, a tool argument, and an env-var suffix — eliminating sanitize-collision risk in
exec expansion.

### 8. ES-backed session store, shared client, isolated index

`app.py` constructs `ElasticsearchStore(elasticsearch_client=AsyncElasticsearch(**_client_kwargs()),
index_prefix=settings.SESSION_INDEX_PREFIX)` and passes it as
`FastMCP(session_state_store=...)`. Reuses `mcc/db.py::_client_kwargs`. Chosen for
multi-replica safety (any replica serves any session), not durability — session
context is ephemeral.

`ElasticsearchStore` derives index names as `{index_prefix}-{collection}`, and
FastMCP's state store uses the collection `fastmcp_state`. With prefix `mcc-ctx` the
store touches only `mcc-ctx-fastmcp_state`, which cannot collide with MCC's own indices
(`mcc-users`, `mcc-tools`, `mcc-keys`). The prefix is a new setting
(`session_index_prefix`, default `"mcc-ctx"`) rather than hardcoded, mirroring the
existing `user_index` / `tool_index` / `key_index` settings. `auto_create=True` only
ever creates the prefixed index.

### 9. current_user_var stays authoritative; only user_env() is removed

This change removes `user_env()` (the function flattening identity into discrete
`MCC_CTX_*` env vars). It does **not** remove `current_user_var` — MCC's own
request-scoped `ContextVar` set by `AuthMiddleware` from the validated auth token.
That var remains the single authoritative source of identity and is still required to:
resolve `username` for the scope key in `get_context`/`set_context`; populate the
reserved identity keys when `execute` assembles the snapshot; and drive RBAC
(`tool.allows(user)` needs the full `UserModel`).

The stored `context` blob carries a **snapshot** of identity (`user/email/groups/tools`)
for tools to read, but identity is **re-derived from `current_user_var` every request
and merged over the stored vars (identity wins)**. The blob is never authoritative for
identity — trusting it would let a stale or tampered blob outlive a permission change
or impersonate, which the reserved-key rule (decision 4) exists to prevent. (Note:
there is no FastMCP "current_user" contextvar; identity resolution is entirely MCC's.)

### 10. TTL

Keep FastMCP's default session-state TTL (`_STATE_TTL_SECONDS = 86400`, 24h). No new
setting.

### 11. Missing key and value typing

`set_context`'s `value` accepts any JSON type and is stored typed; only exec-env
expansion flattens to string. `get_context` returns the value **JSON-encoded** (an
unset name yields the literal `null`): the structured tool result already preserves
type, but the human-readable text block FastMCP also emits is always stringified, so
returning JSON keeps that block unambiguous — `"1000"` (string) vs `1000` (number) vs
`null` — to a reader that sees only the text. Callers decode with `json.loads`.

## Propagation summary

```
                        ONE context dict (per session, per user)
   { user, email, groups, tools,        ← reserved identity (RO via set)
     <slug>: <any-json>, ... }           ← mutable vars

   fn tool                              exec tool
   ───────                              ─────────
   MCC_CTX = <whole dict as JSON>       MCC_CTX_USER=alice
        │                               MCC_CTX_GROUPS=admin,osint
   pyrunner: json.loads(MCC_CTX)        MCC_CTX_BUDGET=1000
        │ (only if declared)            MCC_CTX_FILTERS={"a":1}   (json string)
   fn(..., context={...})  typed        (no MCC_CTX blob)
```

## Open risks

- `session_id` derives from a client-supplied header for HTTP; a client reusing
  another live session's id lands in that bucket. The `(session, user)` key bounds the
  blast radius to one identity. Documented, not further defended here.
- Per-call ES read in `execute` to assemble the snapshot. Small; acceptable. Can be
  revisited with request-scoped memoization if it shows up in profiling.
