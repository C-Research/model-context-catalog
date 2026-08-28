## Why

MCC has a persisted, queryable audit trail for tool *calls* (`mcc/audit.py`, gated on `settings.audit_index`), but nothing records who searched the catalog for what, or which tool keys a search actually surfaced to them. Discovery is half the interaction with MCC (`search` before `execute`) and today it leaves no trace beyond an ephemeral log line. There is also no way to *view* either audit trail short of hand-writing a query against the storage backend — no CLI command reads either index back out.

## What Changes

- **BREAKING**: rename the `audit_index` setting to `audit_tool_index` (same semantics — empty string disables auditing, non-empty names the index). Anyone with `audit_index` set in `settings.local.yaml` or `MCC_AUDIT_INDEX` must rename it.
- Add a new `audit_search_index` setting, `""` by default (disabled), independently toggling a new search-audit trail.
- Add `SearchAuditIndex`, mirroring the existing `AuditIndex`: one record per `search()` call, capturing the caller, the query text, the effective `min_score`, and the ordered list of tool keys (with scores) that were actually returned to that caller after RBAC filtering — never the full tool signature/description.
- Refactor `search()` in `mcc/app.py` to compute the RBAC-filtered `(tool, score)` list once, shared by both the audit record and the response text, so the audit path never touches `tool.signature`.
- Extend `IndexBase.search()` on both storage backends (`mcc/db/es.py`, `mcc/db/os.py`) with `limit`/`offset`/`sort` parameters (renaming the existing `size` parameter to `limit`), needed to page audit records back out newest-first.
- Add a new `mcc audit` CLI command group with two subcommands, `mcc audit tool` and `mcc audit search`, each rendering a `rich` `Table` of records newest-first, paginated with `--offset`/`--limit` (default `0`/`20`), filterable by `--user`/`--since` (`--tool-key` for `tool`, `--query` for `search`). Either subcommand reports plainly, without querying an empty index name, when its backing setting is unset.

## Capabilities

### New Capabilities
- `search-audit-log`: opt-in, persisted audit trail of `search()` calls — who searched what, and which tool keys (with scores) were returned to them.

### Modified Capabilities
- `tool-call-audit-log`: the enabling setting is renamed from `audit_index` to `audit_tool_index`; behavior is otherwise unchanged.
- `admin-cli`: adds the `mcc audit tool` / `mcc audit search` command group for reading back both audit trails as paginated, filterable rich tables.

## Impact

- `mcc/settings.yaml` — rename `audit_index` → `audit_tool_index`; add `audit_search_index`.
- `mcc/audit.py` — `AuditIndex` reads the renamed setting; add `SearchAuditIndex` and `_record_search`.
- `mcc/app.py` — `search()` refactored to share one RBAC-filtered result list between the audit call and the response.
- `mcc/db/es.py`, `mcc/db/os.py` — `IndexBase.search()` signature change (`size` → `limit`, plus new `offset`/`sort`); existing call sites using `size=` must update.
- `mcc/cli/` — new `audit` command group, registered in `mcc/cli/__init__.py`.
- Any deployment with `audit_index`/`MCC_AUDIT_INDEX` set must rename it to `audit_tool_index` on upgrade.
