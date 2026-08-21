## ADDED Requirements

### Requirement: Rate limit middleware
The server SHALL register a rate-limit middleware, innermost in the middleware chain, that limits how often a given user can invoke a given catalog tool through the `execute` MCP tool. The middleware SHALL be registered only when `rate_limit.enabled` is `true` in settings; when disabled (the default), no rate-limit middleware SHALL be registered and behavior SHALL be unchanged from before this middleware existed.

The middleware SHALL apply only to calls where the MCP tool name is `execute`. It SHALL NOT limit calls to `search`, `whoami`, `describe_tools`, `set_session`, or `get_session`.

For an `execute` call, the middleware SHALL resolve the rate-limit subject from the call's `key` argument (the catalog tool key, e.g. `admin.shell`). If the `key` argument is missing or not a string, the middleware SHALL skip the rate-limit check and allow the call to proceed to the `execute` handler unmodified.

Each `rate_limit.default`/`rate_limit.tools.<key>` value in settings SHALL be either the integer `-1` (unlimited) or a string of the form `"<count>/<n><unit>"` where `unit` is `s`, `min`, or `hr` (e.g. `"60/1min"`, `"50/24hr"`, `"10/30s"`). The middleware SHALL parse these values into a `(limit, period_seconds)` pair once, at middleware construction time, and SHALL raise an error immediately (at construction, not on a live request) if any configured value does not match this format.

The middleware SHALL resolve the applicable `(limit, period)` for a subject tool key by checking `rate_limit.tools.<key>` first, falling back to `rate_limit.default` if no tool-specific entry exists. A resolved `limit` of `-1` SHALL be treated as unlimited — the middleware SHALL allow the call without incrementing or checking any counter.

The middleware SHALL track call counts using a fixed time window, keyed per user and per tool: `ratelimit:{username-or-anon}:{tool_key}`. Unauthenticated callers SHALL share a single `anon` bucket per tool. A window SHALL reset a `period`-seconds duration after the first call recorded in that window, independent of a rolling/sliding average.

Cache hits within `execute()` (tool results returned from `cache_ttl`) SHALL still count as a call against the rate limit — the middleware SHALL NOT distinguish a call that will be served from cache from one that will actually execute the tool.

When a call exceeds the resolved limit, the middleware SHALL NOT invoke the downstream handler. It SHALL instead return a plain-text tool result (no error flag) stating which tool was throttled and the number of seconds remaining until the window resets, so an LLM caller receives actionable text rather than a transport-level error.

#### Scenario: Rate limiting disabled
- **WHEN** `rate_limit.enabled` is `false` or unset
- **THEN** no rate-limit middleware is registered and `execute` calls are never throttled

#### Scenario: Call within limit
- **WHEN** a user calls `execute` with a tool key whose current-window count is at or below its resolved limit
- **THEN** the call proceeds normally and the count for that user/tool/window is incremented

#### Scenario: Call exceeds limit
- **WHEN** a user calls `execute` with a tool key whose current-window count has already reached its resolved limit
- **THEN** the middleware returns a plain-text result reporting the throttled tool key and seconds remaining in the window, and the `execute` handler is never invoked

#### Scenario: Tool-specific limit overrides default
- **WHEN** `rate_limit.tools` contains an entry for the called tool key
- **THEN** that entry's parsed `(limit, period)` is used instead of `rate_limit.default`

#### Scenario: Unlimited tool
- **WHEN** the resolved limit for a tool key is `-1`
- **THEN** the call proceeds without any counter being checked or incremented

#### Scenario: Rate string parsed into limit and period
- **WHEN** a configured value is `"60/1min"`
- **THEN** it resolves to a limit of 60 calls per 60-second window (and analogously for `"min"`/`"hr"`/`"s"` units and other counts)

#### Scenario: Malformed rate string fails fast
- **WHEN** a configured `rate_limit.default` or `rate_limit.tools.<key>` value is neither `-1` nor a valid `"<count>/<n><unit>"` string
- **THEN** the middleware raises an error at construction time, before any request is handled

#### Scenario: Missing or malformed key argument
- **WHEN** an `execute` call has no `key` argument or a non-string `key` argument
- **THEN** the rate-limit middleware skips its check and passes the call through to the `execute` handler unmodified

#### Scenario: Non-execute verbs are never limited
- **WHEN** a user calls `search`, `whoami`, `describe_tools`, `set_session`, or `get_session`
- **THEN** the rate-limit middleware never applies a check, regardless of settings

#### Scenario: Anonymous callers share one bucket per tool
- **WHEN** two different unauthenticated callers invoke the same catalog tool
- **THEN** both calls count against the same `anon` bucket for that tool

#### Scenario: Cache hit still counts
- **WHEN** an `execute` call would be served entirely from `execute()`'s own result cache
- **THEN** the call still increments the rate-limit counter for that user and tool

#### Scenario: Throttled calls remain logged and timed
- **WHEN** a call is rejected by the rate-limit middleware
- **THEN** the existing logging and timing middleware still record the call, the same as any other completed call
