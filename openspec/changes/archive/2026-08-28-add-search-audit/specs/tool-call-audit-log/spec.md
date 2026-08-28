## MODIFIED Requirements

### Requirement: Audit logging is opt-in via a settings string
The server SHALL persist an audit record for a catalog tool call only when the `audit_tool_index` setting is a non-empty string, which SHALL also be used as the index/collection name for storage. When `audit_tool_index` is unset or empty (the default), no audit hook SHALL be registered and no audit records SHALL be written, with no other behavior change.

#### Scenario: Auditing disabled by default
- **WHEN** `audit_tool_index` is unset or `""`
- **THEN** no audit record is written for any tool call, and the server's behavior is otherwise unaffected

#### Scenario: Auditing enabled by setting a name
- **WHEN** `audit_tool_index` is set to a non-empty string, e.g. `"mcc-audit"`
- **THEN** audit records for subsequent tool calls are written to an index/collection with that name
