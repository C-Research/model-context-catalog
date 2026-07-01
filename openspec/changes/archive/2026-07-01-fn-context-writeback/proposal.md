## Why

Today the session context flows one way into fn tools: `execute` assembles the
context dict, pyrunner injects it as the `context` kwarg, and the tool reads it.
The only way to *write* session state is for the LLM to call `set_session`
explicitly. This forces any value a tool wants to persist to travel back out
through the tool's result and into the model's context window before the LLM can
re-stash it — including secrets (a login token, an API cursor), which then leak
into transcripts, logs, and token usage.

Letting an fn tool write its own session context closes the loop: a tool can
stash a value directly (`context["cursor"] = 6`) and a later tool reads it,
without the value ever passing through the LLM.

## What Changes

- After an fn tool runs, its (possibly mutated) `context` dict is propagated back
  into session state — a **full replace** of the caller's stored non-identity vars.
- **No tool signature change.** Tools keep `def fn(..., context=None)`. The change
  is entirely in the pyrunner↔server wire format: pyrunner's stdout becomes the
  2-element envelope `[result, context]` (`[result, null]` when the tool declared
  no `context` param, meaning "don't touch state").
- The server unwraps the envelope: `result` returns to the LLM unchanged;
  `context` is validated and written to session state via `ctx.set_state`.
- **Reserved identity keys are enforced on the write path.** Before writing, the
  server strips `RESERVED_KEYS` and re-derives them from the authenticated user
  (`assemble_context`), so a tool cannot spoof, alter, or delete identity.
- **Invalid keys reject the whole write-back and log.** A returned key that fails
  `SLUG_RE` (would break downstream `MCC_CTX_<NAME>` env expansion) causes the
  entire context write-back to be rejected and logged; the tool's `result` is
  still returned to the LLM.
- **exec (shell) tools are out of scope.** They remain read-only — their env-var
  propagation has no return channel and a subprocess cannot mutate its parent env.

## Capabilities

### Modified Capabilities

- `session-context`: adds fn-tool context write-back (tool → session state),
  guarded by the same reserved-key and slug rules as `set_session`.

## Impact

- `mcc/pyrunner.py`: `execute` emits `[result, context]` on stdout — `context` is
  the injected dict when the fn declared a `context` param, else `null`.
- `mcc/exec.py`: fn path unwraps the envelope before `_apply_transform` (transform
  still operates on `result` only); the write-back delta is stashed on a
  request-scoped back-channel contextvar for the server to apply.
- `mcc/app.py`: `execute` reads the back-channel delta after the call, runs it
  through the `set_session` guard (strip reserved → slug-validate → re-derive
  identity), and calls `ctx.set_state`. Write-back is skipped on a cache hit.
- `mcc/context.py`: helper for validating/normalizing a returned context dict
  (reserved-key strip, slug validation) shared with `set_session`.
- `tests/`: pyrunner stdout assertions updated to the envelope; new coverage for
  write-back, reserved-key enforcement, invalid-key rejection, and no-context-param.
- No new dependencies. The pyrunner↔server stdout format changes (internal); tool
  authors and LLM clients see no contract change.

## Known limitations (accepted)

- **Concurrency:** two tool calls in the same session both read-modify-write state
  with no lock. Because write-back is a full replace, last writer wins and may drop
  the other's keys. Accepted for now; noted in design.
- **Cache hits skip write-back:** a cacheable tool only writes state on a cache
  miss (when its body actually runs). Accepted; noted in design.
- **Mutate, don't rebind:** rebinding the local name (`context = {...}`) is
  invisible; only in-place mutation of the injected dict propagates.
