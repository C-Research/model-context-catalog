## ADDED Requirements

### Requirement: Search auditing is opt-in via a settings string
The server SHALL persist an audit record for a `search()` call only when the `audit_search_index` setting is a non-empty string, which SHALL also be used as the index/collection name for storage. When `audit_search_index` is unset or empty (the default), no audit record SHALL be written and no other behavior of `search()` SHALL change.

#### Scenario: Search auditing disabled by default
- **WHEN** `audit_search_index` is unset or `""`
- **THEN** no audit record is written for any `search()` call, and `search()`'s response is otherwise unaffected

#### Scenario: Search auditing enabled by setting a name
- **WHEN** `audit_search_index` is set to a non-empty string, e.g. `"mcc-search-audit"`
- **THEN** audit records for subsequent `search()` calls are written to an index/collection with that name

### Requirement: Audit records reflect only what the caller actually saw
Each search audit record SHALL include the resolved username (or an indication of no authenticated user), the query text, the effective `min_score` (or its absence), and the ordered list of tool keys — each paired with its relevance score — that survived RBAC filtering (`tool.allows(user)`) for that caller. Tool keys and scores excluded by RBAC filtering SHALL NOT appear in the record. The audit-recording code path SHALL only ever receive a tool's `key` and relevance `score` — never its signature, description, or parameters.

#### Scenario: Only accessible results are recorded
- **WHEN** a `search()` call's raw results include tools the calling user cannot access
- **THEN** the audit record's result list omits those tools entirely and includes only the ones returned in the response

#### Scenario: Result order and scores are preserved
- **WHEN** a `search()` call returns tools in a given relevance order with given scores
- **THEN** the audit record's result list preserves that same order and those same scores

#### Scenario: No results is still audited
- **WHEN** auditing is enabled and a `search()` call's query matches no accessible tools
- **THEN** an audit record is written with an empty result list

### Requirement: Results are serialized as ordered key=score text
The audit record's result list SHALL be serialized as `"key=score;key=score"` text, in result order, using the same separator convention as the existing tool-call audit's params serialization (`key=value;key=value`).

#### Scenario: Multiple results serialize in order
- **WHEN** a search returns tools `admin.shell` (score `8.42`) then `public.request` (score `6.10`), in that order
- **THEN** the record's results field is `"admin.shell=8.42;public.request=6.10"`

### Requirement: Audit write failures never affect the search call
A failure while writing a search audit record (e.g. the storage backend is unreachable) SHALL be caught and logged, and SHALL NOT propagate to the caller or alter `search()`'s own response.

#### Scenario: Audit backend unreachable
- **WHEN** search auditing is enabled and the audit storage backend is unreachable at the moment a record would be written
- **THEN** the triggering `search()` call still returns its normal response, and the audit write failure is only logged
