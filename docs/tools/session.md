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
             ▲                    │            ▲
             │ get_session /      │ injected   │ fn: tools that declare
             │ set_session        │ every call │ `context` write it back
          the LLM                 ▼            │
                     fn: MCC_CTX · exec: MCC_CTX_<NAME>
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

When a tool runs, MCC injects the assembled session store (identity + your variables) into the tool's subprocess. The transport differs by tool kind — both are delivered as [environment variables](env-vars.md#session-store-mcc_ctx).

### `fn:` (Python) tools — the `context` argument

A `fn:` subprocess receives the whole store as the `MCC_CTX` env var (a JSON blob). More conveniently, **if your callable declares a parameter named `context`, MCC parses that blob and injects it as the argument** — with real types preserved (lists stay lists, numbers stay numbers). The `context` parameter is hidden from the tool's public signature: the LLM never sees it and is never prompted for it.

```python
def report(target: str, context: dict) -> dict:
    # `target` is supplied by the caller; `context` is injected by MCC.
    return {"target": target, "called_by": context["user"]}
```

A callable with no `context` parameter has nothing injected — the `MCC_CTX` blob is still in the environment for tools that prefer to read it directly.

### `exec:` (shell) tools — `MCC_CTX_<NAME>`

A shell tool can't take a Python argument, so each entry becomes its own env var, `MCC_CTX_<NAME>` (key uppercased). For `alice` in groups `admin`/`osint` who set `budget=1000`:

```yaml
tools:
  - name: whoami_echo
    exec: |
      echo "called by $MCC_CTX_USER"     # alice
      echo "groups json: $MCC_CTX_GROUPS"  # ["admin", "osint"]
      echo "budget: $MCC_CTX_BUDGET"      # 1000
```

### Identity is unspoofable

The injected store is applied **last**, after a tool's own `env:` — so a tool cannot shadow the caller by declaring its own `MCC_CTX_USER`. The identity keys are re-derived from the authenticated request on every call, so a stale or tampered stored value can never impersonate the caller or outlive a permission change. An unauthenticated call still carries `user="anonymous"`. The auth token is never exposed to the subprocess.

## Writing session state from a tool

A `fn:` (Python) tool that declares a `context` parameter can **persist** state, not just read it: whatever it leaves in the `context` dict when it returns replaces the caller's stored session variables. This lets a tool stash a value (a pagination cursor, an auth token obtained from a backend) directly, so a later tool reads it — without the value ever passing through the LLM.

```python
def paginate(cursor: int = 0, context: dict = None) -> list:
    page, next_cursor = fetch(cursor)
    context["cursor"] = next_cursor   # persisted for the next tool call
    return page
```

Rules and guarantees:

- **Mutate, don't rebind.** Change the dict in place (`context["x"] = 1`, `del context["x"]`). Reassigning the name (`context = {...}`) rebinds a local and is **not** observed.
- **Full replace.** The returned dict fully replaces the caller's non-identity variables — deleting a key removes it from the store.
- **Reserved keys are enforced.** A tool cannot set, alter, or delete `user`, `email`, `groups`, or `tools`; they are stripped from the write-back and re-derived from the authenticated caller. Spoofing is impossible.
- **Invalid keys reject the whole write-back.** If the tool leaves a key that is not a valid slug (lowercase letters, digits, underscores; would break `MCC_CTX_<NAME>` for downstream tools), the entire write-back is rejected and logged. The tool's result is still returned to the LLM.
- **`exec:` (shell) tools are read-only.** A subprocess cannot mutate its parent's environment, so shell tools receive session state but cannot write it back. Use a `fn:` tool if you need to persist state.

!!! note "Two limitations to be aware of"
    - **Concurrency:** concurrent tool calls in the same session both read-modify-write the store with no lock. Because write-back is a full replace, the last writer wins and can drop another call's keys.
    - **Cached tools:** a tool with a `cache_ttl` only writes state on a cache **miss** (when its body actually runs); a cache hit returns the prior result without re-writing state.
