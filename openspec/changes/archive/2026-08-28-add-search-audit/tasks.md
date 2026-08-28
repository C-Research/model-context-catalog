## 1. Settings

- [x] 1.1 Rename `audit_index` → `audit_tool_index` in `mcc/settings.yaml` (keep the `""`-disables-by-default comment, update it to reference the new name)
- [x] 1.2 Add `audit_search_index: ""` to `mcc/settings.yaml`, adjacent to `audit_tool_index`, with a comment mirroring the existing one (empty disables, non-empty names the index)

## 2. Storage backend: paginated, sortable `IndexBase.search()`

- [x] 2.1 In `mcc/db/es.py`, change `IndexBase.search(self, query: dict, size: int = 10000)` to `search(self, query: dict, limit: int = 10000, offset: int = 0, sort: list | None = None)`; pass `size=limit`, `from_=offset`, and `sort=sort` (only when not `None`) to `self._client.search(...)`
- [x] 2.2 In `mcc/db/os.py`, change `IndexBase.search(self, query: dict, size: int = 10000)` to the same `limit`/`offset`/`sort` signature; add `"from": offset` and, when not `None`, `"sort": sort` to the request body alongside `"size": limit`
- [x] 2.3 Confirm no existing call site (`mcc/auth/db.py`, `mcc/auth/keys.py`) passes `size=` by keyword — all call `.search(query_dict)` positionally with the default, so the rename is a no-op for them; add a one-line note only if any site is found passing `size=` explicitly

## 3. `SearchAuditIndex` and recording

- [x] 3.1 In `mcc/audit.py`, update `AuditIndex.index` to read `settings.AUDIT_TOOL_INDEX` (was `settings.AUDIT_INDEX`) and the module-level enable check (`if settings.AUDIT_INDEX:` → `if settings.AUDIT_TOOL_INDEX:`)
- [x] 3.2 Add `SearchAuditIndex(IndexBase)` with `index = settings.AUDIT_SEARCH_INDEX` and a mapping: `timestamp` (date), `username` (keyword), `query` (text), `min_score` (float), `results` (text)
- [x] 3.3 Add a `_serialize_results(pairs: list[tuple[str, float]]) -> str` helper producing `"key=score;key=score"` in input order, reusing the same `;`/`=` convention as `_serialize_params`
- [x] 3.4 Add `async def _record_search(username: str | None, query: str, min_score: float | None, pairs: list[tuple[str, float]]) -> None`, building the doc (`timestamp`, `username`, `query`, `min_score`, `results` via `_serialize_results`) and writing it to `SearchAuditIndex` with a generated `uuid4()` id, wrapped in the same best-effort `try/except Exception: logger.exception(...)` as `_record_call`
- [x] 3.5 Gate `SearchAuditIndex`/`_record_search` registration on `if settings.AUDIT_SEARCH_INDEX:` — no hook registry; `mcc/app.py`'s `search()` calls `_record_search` directly (see §4), so this is just importable, not self-registering

## 4. `search()` refactor in `mcc/app.py`

- [x] 4.1 Replace the single `accessible` comprehension with `allowed = [(tool, score) for tool, score in results if tool.allows(user)]`
- [x] 4.2 After computing `allowed`, if `settings.AUDIT_SEARCH_INDEX`, call `await mcc.audit._record_search(username, query, min_score, [(tool.key, score) for tool, score in allowed])` (import `mcc.audit` at module level alongside the existing `import mcc.audit` in `mcc/app.py`, or import the specific function — match whatever import style keeps `mcc.audit` a single import per project convention of module-level imports only)
- [x] 4.3 Derive the "no results" and response-text branches from `allowed` instead of the old `accessible` list, preserving the existing `f"[{score:.2f}]\n{tool.signature}"` formatting and no-match message exactly
- [x] 4.4 Resolve `username` the same way `middleware.display_username` does (or reuse it) so search audit records use the same `"alice"` / `"alice<a@b.com>"` / `"anonymous"` convention as tool-call logging

## 5. `mcc audit` CLI command group

- [x] 5.1 Create `mcc/cli/audit.py` with a `@click.group() def audit()` docstring "View persisted audit logs."
- [x] 5.2 Add a shared internal helper that builds an ES/OS sort-by-timestamp-desc query from optional `user`/`since` (and a type-specific extra term) filters, calls `IndexBase.search(query, limit=limit, offset=offset, sort=[{"timestamp": "desc"}])`, and returns the doc list — used by both subcommands
- [x] 5.3 Add `audit.command("tool")` with `--offset/-o` (default 0), `--limit/-l` (default 20), `--user`, `--tool-key`, `--since`; on empty `settings.AUDIT_TOOL_INDEX`, print a plain notice and return; otherwise query `AuditIndex` and render a `rich.table.Table` with columns Timestamp/User/Tool/Status/Duration (Params/Error columns included only when `settings.AUDIT_PARAMS`)
- [x] 5.4 Add `audit.command("search")` with the same `--offset/--limit` defaults plus `--user`, `--query`, `--since`; on empty `settings.AUDIT_SEARCH_INDEX`, print a plain notice and return; otherwise query `SearchAuditIndex` and render a `rich.table.Table` with columns Timestamp/User/Query/MinScore/Results
- [x] 5.5 Register the new `audit` group in `mcc/cli/__init__.py` (`from mcc.cli.audit import audit` / `cli.add_command(audit)`), alongside `tool`/`user`

## 6. Tests

- [x] 6.1 Test `search()` records a `SearchAuditIndex` doc with the correct ordered `results` string when `audit_search_index` is set, and that the doc contains no signature/description/param text
- [x] 6.2 Test `search()` writes no record when `audit_search_index` is unset
- [x] 6.3 Test the audit record's results only include RBAC-accessible tools, in the same order as the response
- [x] 6.4 Test a search-audit write failure (mock the backend to raise) doesn't propagate to `search()`'s caller
- [x] 6.5 Test `IndexBase.search()` on both backends respects `limit`/`offset`/`sort` (or at minimum the ES backend if OS isn't exercised in CI — check existing test setup for backend coverage conventions)
- [x] 6.6 CLI test: `mcc audit tool` and `mcc audit search` each print a plain notice (not an exception) when their setting is unset
- [x] 6.7 CLI test: `mcc audit tool --user`/`--tool-key` and `mcc audit search --user`/`--query` filter as expected against seeded index data
- [x] 6.8 CLI test: `--offset`/`--limit` defaults (0/20) and overrides page correctly

## 7. Checks

- [x] 7.1 `uv run pytest tests/`
- [x] 7.2 `uv run pyright`
- [x] 7.3 `uv run ruff check .`
- [x] 7.4 `uv run bandit -c pyproject.toml -r .`
