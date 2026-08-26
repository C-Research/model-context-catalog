## MODIFIED Requirements

### Requirement: Rate limit middleware
The server SHALL enforce rate limiting, innermost in the middleware chain, that limits how often a given user can invoke a given catalog tool — through the MCP `execute` tool and through the `POST /tools/{key}` HTTP route, sharing the same bucket per tool key. Enforcement SHALL be active only when `rate_limit.enabled` is `true` in settings; when disabled (the default), no rate-limit check SHALL run on either path and behavior SHALL be unchanged from before this middleware existed.

Rate-limit enforcement SHALL apply only to the MCP `execute` tool and the `POST /tools/{key}` HTTP route. It SHALL NOT limit `search`, `whoami`, `describe_tools`, `set_session`, `get_session`, `GET /tools`, or `GET /tools/{key}`.

For an `execute` call, the rate-limit subject is resolved from the call's `key` argument (the catalog tool key, e.g. `admin.shell`). If the `key` argument is missing or not a string, the check is skipped and the call proceeds to the `execute` handler unmodified. For a `POST /tools/{key}` call, the rate-limit subject is the `key` path parameter.

Each `rate_limit.default`/`rate_limit.tools.<key>` value in settings SHALL be either the integer `-1` (unlimited) or a string of the form `"<count>/<n><unit>"` where `unit` is `s`, `min`, or `hr` (e.g. `"60/1min"`, `"50/24hr"`, `"10/30s"`). These values SHALL be parsed into a `(limit, period_seconds)` pair once, at construction time, and SHALL raise an error immediately (at construction, not on a live request) if any configured value does not match this format.

The applicable `(limit, period)` for a subject tool key is resolved by checking `rate_limit.tools.<key>` first, falling back to `rate_limit.default` if no tool-specific entry exists. A resolved `limit` of `-1` SHALL be treated as unlimited — the call SHALL be allowed without incrementing or checking any counter.

Call counts SHALL be tracked using a fixed time window, keyed per user and per tool: `ratelimit:{username-or-anon}:{tool_key}` — the same key format and bucket regardless of whether the call arrived via MCP `execute` or `POST /tools/{key}`. Unauthenticated callers SHALL share a single `anon` bucket per tool. A window SHALL reset a `period`-seconds duration after the first call recorded in that window, independent of a rolling/sliding average.

Cache hits within `execute()` (tool results returned from `cache_ttl`) SHALL still count as a call against the rate limit — a call that will be served from cache is not distinguished from one that will actually execute the tool.

When a call exceeds the resolved limit: on the MCP path, `execute` SHALL NOT be invoked, and a plain-text tool result (no error flag) SHALL be returned stating which tool was throttled and the seconds remaining until the window resets. On the `POST /tools/{key}` path, the tool SHALL NOT be invoked, and the HTTP response SHALL indicate the call was throttled.

#### Scenario: Rate limiting disabled
- **WHEN** `rate_limit.enabled` is `false` or unset
- **THEN** no rate-limit check runs on either the MCP `execute` path or `POST /tools/{key}`, and neither is ever throttled

#### Scenario: Call within limit
- **WHEN** a user calls a tool, via either transport, and the current-window count for that user/tool bucket is at or below its resolved limit
- **THEN** the call proceeds normally and the bucket's count is incremented

#### Scenario: Call exceeds limit
- **WHEN** a user calls a tool, via either transport, and the current-window count for that user/tool bucket has already reached its resolved limit
- **THEN** the tool is not invoked, and the caller receives a response reporting the throttled tool key and seconds remaining in the window

#### Scenario: Tool-specific limit overrides default
- **WHEN** `rate_limit.tools` contains an entry for the called tool key
- **THEN** that entry's parsed `(limit, period)` is used instead of `rate_limit.default`, regardless of which transport the call arrived through

#### Scenario: Unlimited tool
- **WHEN** the resolved limit for a tool key is `-1`
- **THEN** the call proceeds without any counter being checked or incremented

#### Scenario: Rate string parsed into limit and period
- **WHEN** a configured value is `"60/1min"`
- **THEN** it resolves to a limit of 60 calls per 60-second window (and analogously for `"min"`/`"hr"`/`"s"` units and other counts)

#### Scenario: Malformed rate string fails fast
- **WHEN** a configured `rate_limit.default` or `rate_limit.tools.<key>` value is neither `-1` nor a valid `"<count>/<n><unit>"` string
- **THEN** an error is raised at construction time, before any request is handled

#### Scenario: Missing or malformed key argument
- **WHEN** an `execute` call has no `key` argument or a non-string `key` argument
- **THEN** the rate-limit check is skipped and the call passes through to the `execute` handler unmodified

#### Scenario: Non-execute, non-tool-call verbs are never limited
- **WHEN** a user calls `search`, `whoami`, `describe_tools`, `set_session`, `get_session`, `GET /tools`, or `GET /tools/{key}`
- **THEN** no rate-limit check ever applies, regardless of settings

#### Scenario: Anonymous callers share one bucket per tool
- **WHEN** two different unauthenticated callers invoke the same catalog tool, via either transport
- **THEN** both calls count against the same `anon` bucket for that tool

#### Scenario: Cache hit still counts
- **WHEN** an `execute` call would be served entirely from `execute()`'s own result cache
- **THEN** the call still increments the rate-limit counter for that user and tool

#### Scenario: Throttled calls remain logged and timed
- **WHEN** a call is rejected by the rate-limit check, via either transport
- **THEN** the existing logging and timing still record the call, the same as any other completed call

#### Scenario: Bucket shared across transports
- **WHEN** a user calls a tool via `POST /tools/{key}` and then via the MCP `execute` tool for the same key, within the same rate-limit window
- **THEN** both calls count against the same bucket and the combined count is checked against the resolved limit

## ADDED Requirements

### Requirement: Metrics middleware records tool-call counters and duration
The server SHALL record `mcc_tool_calls_total{tool, status}` (a counter) and `mcc_tool_call_duration_seconds{tool}` (a histogram) for every tool call handled via the MCP `execute` tool or the `POST /tools/{key}` HTTP route, using the same shared recording function for both, labeled by the exact catalog tool key.

#### Scenario: MCP execute call recorded
- **WHEN** a catalog tool is called via the MCP `execute` tool
- **THEN** `mcc_tool_calls_total` for that tool key is incremented and its call duration is recorded in `mcc_tool_call_duration_seconds`

#### Scenario: REST tool call recorded
- **WHEN** a catalog tool is called via `POST /tools/{key}`
- **THEN** `mcc_tool_calls_total` for that tool key is incremented and its call duration is recorded in `mcc_tool_call_duration_seconds`, using the same series as an equivalent MCP call

#### Scenario: Failed call recorded with a failure status label
- **WHEN** a tool call raises an exception or fails validation, via either transport
- **THEN** `mcc_tool_calls_total` is incremented with a `status` label indicating failure, distinct from a successful call
