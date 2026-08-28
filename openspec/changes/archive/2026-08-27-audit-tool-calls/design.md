## Context

Every catalog tool call passes through exactly one real choke point regardless of transport: `ToolModel.call()` (`mcc/models.py`). Today three separate mechanisms observe or gate that call from *outside* it, each duplicated once as a FastMCP `Middleware` class (wrapping the MCP `execute` tool) and once as inline code in the REST `POST /tools/{key}` handler (`mcc/routes.py`):

- `LoggingMiddleware` — logs every attempt (including throttled ones) with user/tool/params/timing.
- `MetricsMiddleware` — records `mcc_tool_calls_total`/`mcc_tool_call_duration_seconds`, deliberately excluding throttled calls.
- `RateLimitMiddleware` — vetoes before the tool runs, sharing one bucket across both transports.

This change adds a persisted audit trail (the actual feature request) and uses it as the forcing function to collapse the two duplications that *can* safely collapse — Logging and Metrics move onto a hook fired from inside `ToolModel.call()` itself — while leaving the third (Rate limiting) exactly where it runs today, because it has a hard timing constraint the other two don't.

## Goals / Non-Goals

**Goals:**
- Persist a queryable record of catalog tool calls that actually execute: user, key prefix, tool key, params, duration, success/failure — gated off by default.
- Give `ToolModel` a hook mechanism so this and future call-scoped concerns don't each reinvent "wrap try/except at two call sites."
- Fold `LoggingMiddleware`/`MetricsMiddleware` onto that mechanism, removing their FastMCP-middleware-class + inline-REST duplication.
- Make caller identity (`current_user_var`) uniformly available regardless of transport, since the hook needs it and today it's MCP-only.

**Non-Goals:**
- A read/query HTTP surface for the audit log (`GET /audit` or similar) — explicitly deferred to a follow-up change.
- Any per-param sensitivity marking or redaction beyond "visible params only" — hidden/override params are dropped entirely, not redacted-in-place.
- Index rotation, TTL, or ILM for the audit index — unbounded retention is accepted for v1.
- Moving rate-limit enforcement into the same hook mechanism — see Decisions.

## Decisions

### The hook lives on `ToolModel`, not as a new middleware layer
`ToolModel.call()` already has the shape needed (try/except around the callable invocation, access to `self.key`/`visible_params`). Adding a small event dataclass + a plain list-based registry (`on_tool_call(fn)` appends; `call()` fires in a `finally`) keeps this consistent with the rest of the codebase's style (contextvars, plain functions — no new class hierarchy). Considered: keep using FastMCP `Middleware` subclasses and just add a fourth one for audit. Rejected — that's the exact duplication this change exists to stop; it would also require the REST route to keep hand-rolling its own equivalent, a fourth time.

### Rate limiting stays outside the hook, unlike Logging/Metrics
The existing `mcp-middleware` spec requires "cache hits within `execute()` ... SHALL still count as a call against the rate limit." A cache hit (`app.py`'s `cached(cache_key, _compute, tool.cache_ttl)`) never invokes `_compute`/`ToolModel.call()` on a hit — so a check living inside `call()` cannot see cache hits at all. Rate limiting is therefore kept as an explicit `check_rate_limit()` call in `execute()` (before the cache lookup) and `tool_execute()` (before invocation), exactly where enforcement runs today; only the `RateLimitMiddleware` *class* is deleted, since nothing outside `mcp.add_middleware(...)` depended on it being a `Middleware` subclass specifically.

Logging and Metrics have no equivalent explicit requirement forcing cache-hit visibility, so they move fully into the hook. This is a deliberate, called-out behavior change (see proposal): a cache-hit `execute()` call is no longer logged or metrics-recorded, only rate-limited (unchanged).

### Audit and Metrics hooks filter to `success`/`error`; Logging does not
`ToolCallEvent.status` is `"success"` or `"error"` — there is no `"rate_limited"` status, because rate-limit vetoes happen before `call()` is ever invoked and therefore never produce an event. This means denied/throttled attempts are outside this change's audit trail by construction — only calls whose underlying callable actually ran are recorded.

Logging's existing "throttled calls remain logged" requirement can no longer be satisfied automatically once `LoggingMiddleware` is deleted — today that requirement is only actually met on the MCP path, as a side effect of `LoggingMiddleware` sitting outside `RateLimitMiddleware` in the FastMCP chain (verified: `tool_execute`'s REST-side throttle return has no corresponding log call today at all, despite the spec scenario claiming "either transport"). Rather than let this regress on MCP and stay silently unmet on REST, `execute()` and `tool_execute()` each gain one explicit log call at the point they reject a call for exceeding its rate limit — satisfying the requirement honestly on both transports for the first time, not just preserving an MCP-only accident.

### `audit_index` doubles as the enable flag
Following `user_index`/`tool_index`/`key_index`'s existing convention (plain name strings, no sibling boolean), `audit_index: ""` is disabled; any non-empty value both names the index and turns the hook registration on. This avoids `rate_limit.enabled`-style redundancy (a boolean plus a separately-configured name) for a setting that already has a natural name to piggyback on.

### `audit_params` is a separate on/off switch, default `true`
Independent of whether auditing is on at all, `audit_params: false` drops the params field from every row while still recording user/tool/duration/status. Kept as a flat boolean (not nested under a settings object) for the same reason `audit_index` is flat — consistent with the rest of `settings.yaml`'s top-level index/flag settings.

### Params serialization: `key=var;key=var` text, not a structured field
Elasticsearch/OpenSearch dynamic object mappings risk field-count explosion on an unbounded-retention index once enough distinct tool/param-name combinations have been audited (see Non-Goals: no rotation). A `flattened` field type avoids explosion but adds mapping complexity for marginal benefit here. A single delimited text field is simple, human-greppable, and sufficient — nothing needs to query by a specific param's value today. Only `visible_params` are serialized; hidden/override values are never included, matching the existing `ToolModel.visible_params`/`hidden_params` split.

### Error field is always the concise form, even in `DEBUG`
`f"{type(exc).__name__}: {exc}"`, matching `_error_text()`'s non-debug summary — never a full traceback. Unlike `_error_text()` (which conditionally shows the full traceback to an LLM caller when `settings.DEBUG` is true), the audit log is a persisted, unbounded-retention store read by a human auditor, not fed back into a tool response — full tracebacks (source paths, line numbers) have no legitimate reason to be captured there regardless of debug mode.

### `AuditIndex` lives in `mcc/audit.py`, not `mcc/db/{es,os}.py`
Unlike `UsersIndex`/`KeysIndex`/`ToolIndex` — which are required, always-on parts of the catalog — `AuditIndex` is optional and off by default. Keeping it out of `mcc/db/` keeps that module's always-on surface unchanged; `audit.py` gets it for free without ES/OS branching of its own by importing the newly-exported `IndexBase` (see below) from `mcc.db`.

### `ESIndex`/`OSIndex` renamed to `IndexBase`, exported from `mcc/db`
Today `mcc/db/__init__.py` already dispatches `UsersIndex`/`KeysIndex`/`ToolIndex`/`session_store` to the configured backend; adding `IndexBase` to that same dispatch (backed by the renamed concrete `ESIndex`→`IndexBase` in `es.py`, `OSIndex`→`IndexBase` in `os.py`) means `mcc/audit.py` can write `class AuditIndex(IndexBase)` with zero backend-branching code of its own, and any future optional index gets the same one-line pattern. Verified low blast radius: neither name is referenced outside its own file today.

### Identity uniformity: `current_user_var` set in `route()`, not just `AuthMiddleware`
`AuthMiddleware.on_message` sets `current_user_var` for MCP requests; REST's `route()` decorator (`routes.py`) resolves a user but only ever stored it on `request.scope["user"]`. Since Starlette runs each request in its own asyncio task (the same reason `current_context_var`/`writeback_context_var` already work per-request in `tool_execute` without cross-request leakage), setting `current_user_var.set(user)` in `route()`'s wrapper — alongside the existing `request.scope["user"] = user` line — is safe and makes every custom route uniform with MCP, not just `tool_execute`. No token/reset needed, matching `AuthMiddleware`'s own style.

### Key prefix populated at resolution time, not just in `list_users()`
`UserModel.key` already has the right shape (`{"prefix", "created_at", "expires_at"}`) but today only `list_users()`'s batch enrichment fills it in. Keys are stored one per user, keyed by username, so `get_current_user()` attaches it with a direct `KeysIndex().get(user.username)` lookup after resolving identity — independent of which backend authenticated this particular request. This is deliberately not "only when this request was itself authenticated via an API key": a user who normally logs in via OAuth/JWT may still have a provisioned API key on file for other uses (e.g. CI), and the audit trail should show that key's prefix on their calls regardless of which credential they used to sign in that session. `get_user_by_key()`'s REST path already has this for free — `verify_api_key()` resolves the same record it would look up separately, so it just attaches `user.key` from what it already fetched.

## Risks / Trade-offs

- **[Risk]** Cache-hit calls silently stop appearing in logs/metrics once this ships, which could look like a regression to anyone watching dashboards built on `mcc_tool_calls_total`. → **Mitigation**: called out explicitly in the proposal as a behavior change, not hidden; cache-hit calls were never a large fraction of recorded calls in practice (they exist specifically to *avoid* re-running expensive tools), and rate-limit accounting — the thing that actually matters for cache-hit abuse — is unaffected.
- **[Risk]** `key=var;key=var` param serialization is ambiguous for values containing `;` or `=`. → **Mitigation**: accepted for v1 since nothing parses it back out programmatically; it's for human/grep reading, not structured querying.
- **[Risk]** Unbounded retention on `AuditIndex` grows forever with no rotation. → **Mitigation**: explicitly accepted for v1 (proposal/Non-Goals); an operator who enables `audit_index` takes on managing that index's size the same way they already manage `mcc-users`/`mcc-tools` growth.
- **[Risk]** A bug in the audit hook could, in principle, slow down or break every tool call if not properly isolated. → **Mitigation**: hook failures are caught and logged inside the hook-firing code in `ToolModel.call()`, never propagated — matches the existing `# noqa: BLE001` best-effort pattern used elsewhere (e.g. `readyz`'s backend checks).

## Migration Plan

No data migration — this is new, opt-in functionality. Rollout is: ship with `audit_index: ""` (disabled, no behavior change for existing deployments), an operator opts in by setting `audit_index` to a name in their `settings.local.yaml`. Rollback is the same lever: unset `audit_index` to stop writing (existing audit data is left in place, not deleted). The `LoggingMiddleware`/`MetricsMiddleware`/`RateLimitMiddleware` class removal is not independently toggleable — it ships as part of this change since the hook mechanism replaces their function entirely.

## Open Questions

- None outstanding — all forks raised during design (audit scope, retention, redaction, rate-limit placement, file layout, settings shape) were resolved during exploration. The `GET /audit` read surface is deferred to a separate future change, not an open question within this one.
