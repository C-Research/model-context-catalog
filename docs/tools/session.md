---
icon: lucide/notebook-pen
---

# Session Store

Every tool call carries a **session store**: a single dictionary that bundles the caller's identity with any mutable variables the session has stashed. It serves two purposes:

- **Identity** — a tool can know *who* is calling it (for per-user behavior, audit logging, or scoping downstream requests) without ever seeing the auth token.
- **Scratch space** — an LLM workflow can stash a value once (a target host, a budget, a selected record) and have later tool calls pick it up automatically, instead of re-passing it every time.

It is "one var to rule them all": identity is just a set of reserved keys inside the same dictionary the LLM reads and writes.

```
        ┌──────────────────────────────────────────────┐
        │   session store  (per session, per user)      │
        │                                                │
        │   user, email, groups, tools   ← identity (RO) │
        │   <your vars> …                ← mutable       │
        └──────────────────────────────────────────────┘
                 ▲ get_session / set_session
                 │                       │ injected on every tool call
              the LLM                    ▼
                              fn: MCC_CTX  ·  exec: MCC_CTX_<NAME>
```

## Reserved identity keys

The dictionary always carries these keys, populated from the authenticated user. They are **read-only** — `set_session` refuses to write them, and they are re-derived from the request on every call so a stored value can never impersonate the caller.

| Key | Value |
|-----|-------|
| `user` | The caller's username (`anonymous` when unauthenticated) |
| `email` | The caller's email (present only when the user has one) |
| `groups` | The user's group names (a list) |
| `tools` | Tool keys granted **directly** to the user (a list); indirect access is derivable from `groups` |

## The `get_session` / `set_session` tools

Two catalog tools let the LLM read and write session variables:

### `set_session(name, value)`

Stores one value into the session store.

- `name` must be a slug — lowercase letters, digits, and underscores, not starting with a digit. This single rule keeps a name valid simultaneously as a JSON key, a tool argument, and an environment-variable suffix.
- `value` may be **any JSON type** (string, number, boolean, list, object) and is stored with its type preserved.
- The [reserved identity keys](#reserved-identity-keys) (`user`, `email`, `groups`, `tools`) cannot be set.

### `get_session(name)`

Returns the value previously stored under `name`, **JSON-encoded** so its type is unambiguous — a string comes back quoted (`"10.0.0.5"`), a number bare (`1000`), and lists/objects as JSON. An unset name returns the JSON literal `null`. The reserved identity keys resolve to the authenticated caller's identity. Decode the result with a JSON parser to recover the typed value.

## Example

Stash a target and a budget once, then run tools that consume them without re-passing:

```python
set_session("target", "10.0.0.5")     # "Set 'target'."
set_session("budget", 1000)           # "Set 'budget'."

get_session("target")                 # "10.0.0.5"   (JSON string)
get_session("budget")                 # 1000         (JSON number, not "1000")
get_session("user")                   # "alice"      (reserved identity key)
get_session("never_set")              # null         (JSON null)
```

Any tool executed afterward in the same session receives `target` and `budget` automatically — a Python tool as a `context` argument, a shell tool as `MCC_CTX_TARGET` / `MCC_CTX_BUDGET` environment variables. See [How the session reaches your tools](#how-the-session-reaches-your-tools).

## Scope and lifetime

The store is keyed by **`(session_id, username)`** — it is per-session **and** per-user:

- Two sessions of the same user (e.g. two client tabs) have **separate** buckets — values set in one are not visible in the other.
- Two users never share a bucket, even if their session ids were to collide.
- Anonymous callers use `username="anonymous"` and rely on the session id for isolation.

State is **ephemeral**: it is bounded by the session store's TTL (24 hours by default) and is *not* a durable user profile. Treat it as scratch space for the life of a session, not long-term storage.

## How the session reaches your tools

When a tool runs, MCC injects the assembled session store (identity + your variables) into the tool's subprocess. The shape differs by tool kind:

- **`fn:` (Python) tools** receive the whole dictionary as one JSON env var, `MCC_CTX`, and — if the callable declares a `context` parameter — as a typed `context` argument.
- **`exec:` (shell) tools** receive each entry expanded into its own `MCC_CTX_<NAME>` environment variable.

The propagation rules, the injected `context` argument, and the anti-spoofing guarantees are documented in detail under [Environment Variables → Session store](env-vars.md#session-store-mcc_ctx).
