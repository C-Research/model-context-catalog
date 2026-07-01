## Context

`session-context` (landed) propagates a per-`(session, user)` context dict *into*
tool subprocesses one way:

- fn tools: the whole dict as one JSON env var `MCC_CTX`; pyrunner loads it and
  injects it as the `context` kwarg when the fn declares that param.
- exec tools: each entry expanded into `MCC_CTX_<NAME>` env vars.

Writing state is only possible via the `set_session` MCP tool, called by the LLM.
There is no path for a *tool* to persist a value except by returning it to the LLM
first. This proposal adds a return path for **fn tools only**.

Key structural facts that constrain the design:

- fn tools run in a **subprocess** (`pyrunner.py`) that MUST NOT import `mcc` and
  may run in a venv without `mcc` installed. It cannot touch Elasticsearch or call
  `ctx.set_state`. The **server process** remains the only writer.
- The subprocess's only success channel is **stdout**, which pyrunner currently
  fills with `json.dumps(result)`. `_communicate_and_return` (exec.py) returns that
  string; `_apply_transform` may post-process it; `execute` (app.py) returns it to
  the LLM.
- Env vars are copied at spawn and are **one-way**; a child cannot write back to the
  parent's environment. Env is not a viable return channel (ruled out below).

## Goals / Non-Goals

**Goals:**
- fn tools can persist session state by mutating the injected `context` dict.
- No tool-author signature change; the `context` kwarg stays exactly as today.
- Reserved identity keys remain untamperable on the write path — same guarantee as
  the read path and `set_session`.
- Subprocess isolation preserved: it never imports `mcc` or touches ES.

**Non-Goals:**
- exec (shell) tool write-back — read-only, out of scope.
- The `from mcc import session` dict-proxy ergonomics — explicitly deferred.
- Concurrency safety / locking for same-session concurrent writes.
- Key-level delta / merge semantics — this is a full replace.

## Decisions

### 1. Return channel: stdout envelope `[result, context]`

pyrunner's stdout becomes a 2-element JSON array: `[result, context]`. The server
unwraps it — element 0 is the tool result (returned to the LLM, coerced/transformed
exactly as today), element 1 is the context dict to write back.

**Chosen over** a sidecar temp file (`MCC_CTX_OUT`) and an extra fd (fd 3). All
three are viable; the stdout envelope keeps everything on the one channel the
subprocess already uses, with no temp-file lifecycle or fd-inheritance portability
concerns (the codebase already branches on `win32`). The cost — the stdout format
changes for the internal pyrunner↔server contract — is contained to two files we
own plus their tests, and no tool author or LLM client sees it.

**Envelope is always emitted**, for format consistency: a tool that declared no
`context` param yields `[result, null]`. A `null` in slot 1 means "don't touch
state"; this is distinct from `[result, {}]`, which means "clear all non-identity
vars" (a legitimate full-replace outcome — see Decision 4).

### 2. No signature change; pyrunner re-emits the injected dict

pyrunner already holds the reference it injected as `context`. After the call it
re-emits that same object:

```python
# pyrunner.execute, after result = fn(**kwargs)
ctx_out = kwargs[_CTX_PARAM] if _CTX_PARAM in kwargs else None
json.dump([result, ctx_out], real_stdout, default=str)
```

Because it's a **full replace**, there is no diffing or change-tracking — the final
state of the dict is the truth, whatever the fn did (`context["x"]=1`,
`del context["y"]`, reassign). This catches **mutation, not rebinding**: a tool that
does `context = {...}` rebinds the local name and the change is invisible. Mutate in
place — the same idiom that already works for reads. Documented, not enforced.

### 3. Result-shape ambiguity is avoided by always unwrapping the envelope

A tool result can itself be a list, so stdout may be a list wrapping a list. The
server ALWAYS unwraps the outer 2-element envelope first, then treats element 0 as
the result regardless of its shape. No code path may confuse "a result that is a
list" with "the envelope." Consistency of the envelope is what removes the ambiguity.

### 4. Full replace of non-identity vars, guarded like `set_session`

The returned `context` fully replaces the caller's stored **non-identity** vars.
Before `ctx.set_state`, the server runs the returned dict through the same gauntlet
as `set_session`, applied to N keys at once:

```
returned dict
  → strip RESERVED_KEYS            (identity is never tool-controllable)
  → slug-validate remaining keys   (they become MCC_CTX_<NAME> for downstream tools)
  → assemble_context(delta, user)  (identity re-derived from current_user_var, wins)
  → set_state
```

The reserved-key **outcome** differs from `set_session` on purpose:

| | `set_session` (LLM) | write-back (tool) |
|---|---|---|
| Reserved key present | **refuse** (error, no write) | **strip silently** |
| Invalid slug key | refuse | **reject whole write-back + log** |
| Identity source | re-derived on read | re-derived via `assemble_context` |

Reserved keys are *stripped silently* on write-back, not refused, because
`assemble_context` injects them into every dict the tool receives — so the returned
dict will always contain them. Refusing would fail every write-back. A tool that
maliciously sets `context["user"]="admin"`, or deletes `context["groups"]`, has no
effect: those keys are stripped and re-derived from the authenticated user. This is
the exact "identity wins, merged last" invariant already in `assemble_context`.

Invalid non-reserved slugs are a tool **bug** (they'd break `MCC_CTX_<NAME>`
expansion for the next tool), so the whole write-back is rejected and logged rather
than silently partially applied — a loud signal, not a silent corruption.

### 5. A rejected write-back does not fail the tool call

The tool already ran and produced a `result`. If validation rejects the returned
context (bad slug), the server returns `result` to the LLM as normal, drops the
state change, and logs. The work is not discarded over a state-write problem.

### 6. Write-back crosses exec.py → app.py via a back-channel contextvar

`ctx.set_state` is only reachable in `app.py`'s `execute`; the envelope is unwrapped
in `exec.py`, which has no `Context`. Rather than thread a return value through
`tool.call`'s kwargs-only signature, `exec.py` stashes the unwrapped context delta
on a request-scoped contextvar (mirroring the inbound `current_context_var`), and
`execute` reads it after `tool.call` returns and applies the guarded write. The
delta is set only on the fn path; exec tools leave it unset.

### 7. Transform runs on the result, after unwrapping

For fn tools, `transform` pipes the fn's output as stdin to a shell pipeline. The
envelope must be unwrapped **before** transform so the pipeline sees `result`, not
`[result, context]`. Write-back is independent of transform.

## Ruled out: env vars as a return channel

Considered per discussion. At `fork`/`exec` the child gets a **copy** of the
environment; `os.environ[...] = ...` in the child mutates only its copy, and there is
no syscall to write a parent's environment — by design, so children can't tamper with
parents. Env is inbound-only (`MCC_CTX` works because the parent sets it *before*
spawn). The only outbound channels are ones the parent pre-arranges: stdout, stderr,
an extra fd, a temp file, or exit code. Env is simply not in that set. Downstream
tools still "see env changes," but only because the server re-derives their
`MCC_CTX` / `MCC_CTX_<NAME>` from updated session state each spawn — never by reading
a child's env.

## Risks / Trade-offs

- **Concurrency (accepted):** same-session concurrent calls both do read-modify-write
  on `get_state`/`set_state` with no lock; full replace means last writer wins and can
  silently drop the other's keys. Full replace is worse here than a delta would be.
  Accepted for now. If it bites, revisit with a merge/delta or per-session lock.
- **Cache hits skip write-back (accepted):** `execute` wraps the call in
  `cached(...)`; on a hit `_compute` never runs, so no write-back occurs. A cacheable
  tool that also stashes state only writes on the first (miss) call. Noted.
- **Test churn:** every test asserting raw `json.dumps(result)` on pyrunner exec
  stdout must move to the envelope. Grep for these during implementation.

## Migration

Internal wire format only. No YAML, tool-author, or LLM-client changes. Existing fn
tools without a `context` param emit `[result, null]` and behave identically (no
state write). Existing tests on pyrunner stdout need updating to the envelope shape.
