## ADDED Requirements

### Requirement: Audit logging is opt-in via a settings string
The server SHALL persist an audit record for a catalog tool call only when the `audit_index` setting is a non-empty string, which SHALL also be used as the index/collection name for storage. When `audit_index` is unset or empty (the default), no audit hook SHALL be registered and no audit records SHALL be written, with no other behavior change.

#### Scenario: Auditing disabled by default
- **WHEN** `audit_index` is unset or `""`
- **THEN** no audit record is written for any tool call, and the server's behavior is otherwise unaffected

#### Scenario: Auditing enabled by setting a name
- **WHEN** `audit_index` is set to a non-empty string, e.g. `"mcc-audit"`
- **THEN** audit records for subsequent tool calls are written to an index/collection with that name

### Requirement: Audit records only calls whose callable actually executed
An audit record SHALL be written for a catalog tool call, via the MCP `execute` tool or the `POST /tools/{key}` HTTP route, only when `ToolModel.call()` actually invokes the tool's underlying callable — whether it succeeds or raises. A call that is rejected by the rate-limit check, denied by authorization, cancelled during elicitation, or served from `execute()`'s result cache SHALL NOT produce an audit record, since none of those reach `ToolModel.call()`.

#### Scenario: Successful execution is audited
- **WHEN** auditing is enabled and a tool call successfully invokes its underlying callable
- **THEN** one audit record is written with status indicating success

#### Scenario: Failed execution is audited
- **WHEN** auditing is enabled and a tool call's underlying callable raises an exception
- **THEN** one audit record is written with status indicating failure

#### Scenario: Rate-limited call is not audited
- **WHEN** auditing is enabled and a call is rejected by the rate-limit check
- **THEN** no audit record is written for that call

#### Scenario: Cache hit is not audited
- **WHEN** auditing is enabled and an `execute()` call is served entirely from its `cache_ttl` cached result
- **THEN** no audit record is written for that call

### Requirement: Recorded fields
Each audit record SHALL include: the resolved username (or an indication of no authenticated user), the resolved user's current API key prefix if one exists on file — looked up directly, independent of which auth backend authenticated this particular request, since a user who normally authenticates via OAuth/JWT may still have a provisioned API key on file for other uses — the exact catalog tool key, a start timestamp, the call's duration, and a status of success or failure. On failure, the record SHALL include a one-line error summary in the form `f"{type(exc).__name__}: {exc}"` — never a full traceback, regardless of the `settings.DEBUG` value.

#### Scenario: Resolved user has a key on file
- **WHEN** a tool call's resolved user has an API key provisioned, regardless of whether that key was used to authenticate this particular request
- **THEN** the audit record includes that key's prefix

#### Scenario: Resolved user has no key on file
- **WHEN** a tool call's resolved user has no API key provisioned, or the call is unauthenticated
- **THEN** the audit record's key-prefix field is absent or null

#### Scenario: Failure error is a one-line summary even in debug mode
- **WHEN** a tool call's underlying callable raises an exception, regardless of `settings.DEBUG`
- **THEN** the audit record's error field contains only the exception's type and message, never a full traceback

### Requirement: Params inclusion is independently toggleable
The server SHALL include the call's visible parameters (per `ToolModel.visible_params` — hidden/override parameter values are never included, audited or not) in each audit record, serialized as `key=var;key=var` text, when the `audit_params` setting is `true` (the default). When `audit_params` is `false`, the audit record SHALL omit the params field entirely rather than writing it as empty.

#### Scenario: Params included by default
- **WHEN** auditing is enabled and `audit_params` is unset or `true`
- **THEN** each audit record includes a params field serialized as `key=var;key=var` text of the call's visible parameters

#### Scenario: Params excluded when disabled
- **WHEN** auditing is enabled and `audit_params` is `false`
- **THEN** audit records omit the params field entirely, independent of whether the call had any parameters

#### Scenario: Hidden and override parameters are never included
- **WHEN** a tool call includes parameters that are hidden or overridden (per `ToolModel.hidden_params`)
- **THEN** those parameter names and values never appear in the audit record, regardless of the `audit_params` setting

### Requirement: Audit write failures never affect the tool call
A failure while writing an audit record (e.g. the storage backend is unreachable) SHALL be caught and logged, and SHALL NOT propagate to the caller or alter the tool call's own result or error.

#### Scenario: Audit backend unreachable
- **WHEN** auditing is enabled and the audit storage backend is unreachable at the moment a record would be written
- **THEN** the triggering tool call still returns its normal result (or error) to the caller, and the audit write failure is only logged
