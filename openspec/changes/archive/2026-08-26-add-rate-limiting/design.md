## Context

MCC's MCP middleware chain (`mcc/app.py`) is: `AuthMiddleware` → `LoggingMiddleware` → `TimingMiddleware` → `ResponseLimitingMiddleware`. Catalog tools (`admin.shell`, `public.request`, etc.) are not separate MCP tools — every one is invoked through the single `execute` MCP tool. `context.message.name` on an `on_call_tool` hook is therefore always the outer MCP verb (`"execute"`, `"search"`, `"whoami"`, ...), never the catalog tool key; the catalog tool key only appears as `context.message.arguments["key"]` on `execute` calls.

MCC already depends on `cashews` for response caching (`mcc/cache.py`), configured once via `cache.setup(backend)` (default `mem://`, optionally `redis://`).

## Goals / Non-Goals

**Goals:**
- Bound the call rate of individual catalog tools, per user, to stop a single identity from hammering a marketplace tool (HTTP, scraping, shell) in a hosted free-trial context.
- Keep configuration entirely in `settings.yaml` — ops-owned, not author-owned in tool YAML.
- Preserve existing log/timing visibility for throttled calls (a throttled call should look like any other logged, timed call — just fast and rejected).
- Ship disabled by default so existing deployments are unaffected until explicitly configured.

**Non-Goals:**
- Rate limiting the built-in verbs (`search`, `whoami`, `describe_tools`, `set_session`, `get_session`) — only catalog tools reached via `execute`.
- A global per-user cap spanning multiple tools — limits are strictly per (user, tool).
- Sliding-window/smoothed limiting — fixed window only.
- Multi-pod-consistent counting — counters live in the same cache backend as everything else; consistency across pods requires operators to already be using a shared backend (`redis://`), which is an existing property of `mcc/cache.py`, not new work here.
- An escape hatch beyond `limit: -1` — no separate "unlimited" flag or tool-level opt-out mechanism.

## Decisions

**Middleware placement: innermost in the chain.** `fastmcp.server.server.FastMCP._run_middleware` builds the chain via `for mw in reversed(self.middleware): chain = partial(mw, call_next=chain)` — the *last*-registered middleware is innermost, closest to the actual tool call. Registering `RateLimitMiddleware` last (after `ResponseLimitingMiddleware`) means `LoggingMiddleware`/`TimingMiddleware` still wrap a throttled call, so it's logged and timed exactly like a call that returns `"Unauthorized"` from inside `execute()` today. The alternative (placing it outer, e.g. right after `AuthMiddleware`) would make throttled calls invisible in logs — directly undermining the abuse-visibility purpose of the feature.

**Config lives only in `settings.yaml`, not tool YAML.** Rejected extending `ToolModel` with a `rate_limit:` field. Rate limits are an operational/deployment concern (how much abuse a hosted tenant can absorb), not an authoring concern (what a tool does) — keeping it out of tool YAML means changing a limit doesn't require touching or re-adding a tool definition, and it can't drift out of sync between a tool author's YAML and an operator's actual capacity planning.

**Fixed window via `cache.incr`/`cache.get_expire`, not cashews' `rate_limit`/`slice_rate_limit` decorators.** Both decorators bind a single key *template* to a wrapped function at decoration time (`get_cache_key_template(func, key=key, prefix=prefix)`) — they're built for "rate-limit this one function," not "rate-limit an arbitrary key computed per call from request data." Reimplementing the same primitive cashews' own fixed-window decorator uses internally (`backend.incr(key, expire=period)`, reject if the returned count exceeds `limit`) as a small imperative helper in `mcc/cache.py` avoids fighting the decorator API while reusing the exact backend semantics already proven in `mcc/cache.py`. Confirmed via the memory backend's `incr`: TTL is set only on the first increment in a window (`_expire = None if value != 1 else expire`), so the window genuinely resets `period` seconds after the first call in it — not a sliding average.

**Config values are human-readable rate strings, not a `{limit, period}` dict.** Each `rate_limit.default`/`rate_limit.tools.<key>` value is either `-1` (unlimited) or a string `"<count>/<n><unit>"` with unit `s`, `min`, or `hr` — e.g. `"60/1min"`, `"50/24hr"`, `"10/30s"`. A new `parse_rate_limit(value: int | str) -> tuple[int, int]` in `mcc/cache.py` (alongside `over_limit`) converts this into the `(limit, period_seconds)` pair `over_limit` actually operates on. `RateLimitMiddleware.__init__` parses `settings.rate_limit.default` and every `settings.rate_limit.tools.*` entry once, at middleware construction time (which happens at `mcc/app.py` import time, since the middleware is only constructed when `rate_limit.enabled` is true) — a malformed string (bad unit, missing `/`, non-numeric count) raises `ValueError` immediately at startup, not on a live request. `on_call_tool` then does a plain dict lookup against the pre-parsed tuples, so parsing cost is paid once per process, not once per call.

**Rejection returns a plain-text `ToolResult`, not a raised error.** `execute()` already has a convention of returning informative strings for caller-facing failure modes (`"Unauthorized"`, tool-validation errors) rather than raising, so the LLM sees actionable text as ordinary tool output instead of a transport-level error it may not handle well. `on_call_tool`'s `call_next` resolves to a `fastmcp.tools.base.ToolResult`, whose constructor accepts a bare string for `content`. Short-circuiting with `return ToolResult(f"Rate limit exceeded for {tool_key} — retry in {n}s.")` (no `is_error`) matches that convention exactly, and `n` is available directly from `cache.get_expire(key)`.

**Key resolution special-cases `execute`.** `RateLimitMiddleware.on_call_tool` only acts when `context.message.name == "execute"`, extracting the subject tool key from `context.message.arguments.get("key")`. If that key is missing or malformed, the middleware skips the check entirely and calls through — `execute()`'s own "Unknown tool" handling in `mcc/app.py` is the single source of truth for key validity; the middleware does not duplicate it.

**Key format:** `f"ratelimit:{user.username if user else 'anon'}:{tool_key}"`. All unauthenticated callers share one `anon` bucket per tool. Accepted: production deployments are expected to have only identified users, so this primarily protects against anonymous abuse in aggregate rather than isolating individual anonymous callers.

**`-1` means unlimited**, checked before touching the cache at all — a tool (or the `default`) configured with `-1` skips the counter entirely rather than paying for an increment that's never enforced.

**Cache hits count against the limit.** `execute()`'s own `cache_ttl` result cache is checked inside the tool body, strictly after `RateLimitMiddleware` has already run. Making cache hits "free" would require moving the rate-limit check inside `execute()`, after its cache lookup — which abandons the middleware-based design entirely for a narrower win. Decision: count every call to `execute` with a given tool key, cache hit or not. This is deliberate, not an oversight.

**Settings shape** (new block in `mcc/settings.yaml`, under `default:`, alongside the existing `cache:` block):

```yaml
rate_limit:
  enabled: false
  default: "60/1min"
  tools:
    admin.shell: "5/1min"
    public.request: -1
```

Resolution order: `rate_limit.tools.<key>` if present, else `rate_limit.default` — both already parsed into `(limit, period_seconds)` tuples at construction time (see above). When `rate_limit.enabled` is false (default), `RateLimitMiddleware` is not registered in `mcc/app.py` at all — zero overhead and zero behavior change for deployments that haven't opted in.

## Risks / Trade-offs

- **Multi-pod undercounting** → each pod tracks independent counters against the shared `cache` object (default `mem://`); on N pods the effective limit is `configured_limit × N` unless the backend is switched to `redis://`. Mitigation: document this in the settings comment next to `rate_limit:`, same as the existing `event_store.backend` comment documents the same tradeoff for stream resumability. Not solved by this change.
- **Anonymous bucket is coarse** → all anonymous callers to a given tool share one counter, so one anonymous abuser can exhaust the budget for all other anonymous callers of that tool. Accepted per Goals — production is expected to run with identified users only.
- **Cache hits still cost budget** → a tool with a generous `cache_ttl` and a tight rate limit could throttle callers who are only ever hitting the cache. Accepted trade-off for keeping the check entirely in middleware, ahead of `execute()`'s own cache lookup.
- **`-1` is a slightly unusual sentinel** → clear once documented, but worth a comment in `settings.yaml` next to the field so it isn't mistaken for a typo'd limit.
- **String parsing is one more thing that can be malformed** → a typo'd unit (`"60/1minute"` instead of `"60/1min"`) or missing slash fails loudly at middleware construction (process startup, when `rate_limit.enabled` is true), not silently — accepted, since fail-fast on a config typo is preferable to fail-fast being deferred to the first request that hits it.

## Migration Plan

Purely additive and disabled by default (`rate_limit.enabled: false`). No migration needed for existing deployments. An operator opts in by adding a `rate_limit:` block (or setting `enabled: true` plus at least a `default`) to their `settings.local.yaml` or environment-specific settings file. Rollback is deleting/disabling that block — no data or schema to migrate since rate-limit counters are ephemeral cache entries with their own TTL.
