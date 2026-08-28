## ADDED Requirements

### Requirement: audit tool command
`mcc audit tool [--offset 0] [--limit 20] [--user <username>] [--tool-key <key>] [--since <date>]` SHALL query the tool-call audit index (`audit_tool_index`), sorted by timestamp descending, and render the matching page of records as a `rich` table with columns for timestamp, user, tool key, status, duration, and (when `audit_params` is enabled) params/error. `--offset` and `--limit` SHALL default to `0` and `20` respectively.

#### Scenario: Default paging
- **WHEN** `mcc audit tool` is run with no options
- **THEN** the 20 most recent tool-call audit records are printed as a table, newest first

#### Scenario: Filtering by user
- **WHEN** `mcc audit tool --user alice` is run
- **THEN** only records for `alice` are printed

#### Scenario: Filtering by tool key
- **WHEN** `mcc audit tool --tool-key admin.shell` is run
- **THEN** only records for that tool key are printed

#### Scenario: Auditing not configured
- **WHEN** `mcc audit tool` is run and `audit_tool_index` is unset or `""`
- **THEN** the command prints a plain notice that tool-call auditing is not configured, without attempting to query a backend index

### Requirement: audit search command
`mcc audit search [--offset 0] [--limit 20] [--user <username>] [--query <text>] [--since <date>]` SHALL query the search audit index (`audit_search_index`), sorted by timestamp descending, and render the matching page of records as a `rich` table with columns for timestamp, user, query, min score, and results. `--offset` and `--limit` SHALL default to `0` and `20` respectively.

#### Scenario: Default paging
- **WHEN** `mcc audit search` is run with no options
- **THEN** the 20 most recent search audit records are printed as a table, newest first

#### Scenario: Filtering by user
- **WHEN** `mcc audit search --user alice` is run
- **THEN** only records for `alice` are printed

#### Scenario: Filtering by query text
- **WHEN** `mcc audit search --query shell` is run
- **THEN** only records whose query text matches are printed

#### Scenario: Auditing not configured
- **WHEN** `mcc audit search` is run and `audit_search_index` is unset or `""`
- **THEN** the command prints a plain notice that search auditing is not configured, without attempting to query a backend index
