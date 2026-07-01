## 1. pyrunner.py (wire format)

- [x] 1.1 In `execute`, after `result = fn(**kwargs)`, capture `ctx_out = kwargs[_CTX_PARAM] if _CTX_PARAM in kwargs else None`
- [x] 1.2 Emit `[result, ctx_out]` as the stdout JSON instead of bare `result` (keep `default=str`); await/run coroutine result before wrapping
- [x] 1.3 Update the module/`execute` docstring to describe the `[result, context]` envelope and the `null` (no context param) case

## 2. context.py (shared validation)

- [x] 2.1 Add a helper (e.g. `sanitize_writeback(returned: dict, user) -> dict | None`) that strips `RESERVED_KEYS`, validates every remaining key against `SLUG_RE`, returns `None` (reject) on any invalid key, else `assemble_context(stripped, user)`
      _(stores bare stripped vars — identity re-derived on read, matching set_session convention)_
- [x] 2.2 Add a request-scoped back-channel contextvar (e.g. `writeback_context_var`) mirroring `current_context_var`, defaulting to a sentinel meaning "no write-back"

## 3. exec.py (unwrap + stash)

- [x] 3.1 In the fn path (`_make_callable` / fn `_spawn`), after `_communicate_and_return` returns a success `str`, parse the `[result, context]` envelope; on parse failure treat as no write-back and pass the raw string through (tolerant, like `_load_context`)
- [x] 3.2 Set element 0 as the effective result for transform + return; stash element 1 on `writeback_context_var` (only on the fn path; leave unset for exec tools)
- [x] 3.3 Ensure `_apply_transform` receives the unwrapped `result`, never the envelope
- [x] 3.4 Failure envelopes (non-zero exit → tuple) are unaffected: no unwrap, no write-back

## 4. app.py (guarded write)

- [x] 4.1 In `execute`, after `_compute` completes (cache miss path only), read `writeback_context_var`; if a write-back was produced, run it through `sanitize_writeback`
- [x] 4.2 On success, `await ctx.set_state(state_key(user), sanitized)`; on reject (`None`), log and skip the write — do NOT fail the call
- [x] 4.3 Confirm cache HIT path never runs `_compute` → no write-back (document/note); reset the contextvar per call to avoid leakage across executions
- [x] 4.4 Confirm `result` return to the LLM is unchanged

## 5. Tests

- [x] 5.1 Update existing pyrunner exec stdout assertions to the `[result, context]` envelope shape
- [x] 5.2 Write-back happy path: fn sets `context["cursor"]=6` → later `get_session`/next tool sees `cursor=6`
- [x] 5.3 No context param → `[result, null]` → stored vars unchanged
- [x] 5.4 Empty `{}` clears non-identity vars; identity keys still present on next read
- [x] 5.5 Reserved-key spoof: `context["user"]="admin"` → stored `user` re-derived, not `admin`
- [x] 5.6 Reserved-key delete: `del context["groups"]` → still present on next read (folded into spoof test)
- [x] 5.7 Invalid slug (`"bad key"`) → whole write-back rejected + logged, result still returned, stored vars unchanged
- [x] 5.8 Result that is a list → unwrapped correctly, list returned as result
- [x] 5.9 exec tool → no write-back (read-only) — covered by existing exec context tests + is_fn gate
- [x] 5.10 Transform on an fn tool operates on `result`, not the envelope

## 6. Docs

- [x] 6.1 `docs/tools/session.md`: document that fn tools can persist state by mutating `context`; mutate-don't-rebind; reserved keys enforced; invalid keys reject; exec tools read-only
- [x] 6.2 `docs/tools/env-vars.md`: note the write-back return path in the propagation deep-dive; env is not a return channel
- [x] 6.3 Note the accepted concurrency race and cache-hit-skips-write-back limitations (session.md note block)

## 7. Verify

- [x] 7.1 `uv run pytest tests/` — 271 passed
- [x] 7.2 `uv run ruff check` — clean
- [x] 7.3 `uv run pyright` — changed mcc/ files clean; 2 net-new test errors match the existing sibling test's union-subscript pattern (project baseline is 267)
