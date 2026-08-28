## Context

`mcc/audit.py` already persists an opt-in audit trail of tool *calls*: `AuditIndex`, gated on `settings.audit_index`, fed by a hook (`on_tool_call` in `mcc/models.py`) fired from `ToolModel.call()` — the one chokepoint both the MCP `execute()` tool and the `POST /tools/{key}` HTTP route funnel through.

`search()` (`mcc/app.py`) has no equivalent trail, and structurally can't reuse the same hook: there is no `/search` HTTP route (checked `mcc/routes.py` — only `/tools` and `/tools/{key}` exist), so `search()` is the *only* call site. `search()` also isn't wrapped in `cached()` the way `execute()`/`whoami()` are, so there's no cache-hit-skips-audit case to account for (unlike tool-call auditing, which explicitly must not audit an `execute()` cache hit).

Separately, neither audit trail can be read back today except by querying the storage backend directly — `IndexBase.search(query, size)` returns up to 10000 unsorted matches with no pagination, and there's no CLI surface for it at all.

## Goals / Non-Goals

**Goals:**
- Persist who searched, what they searched for, and which tool keys (with scores) were actually returned to them, post-RBAC-filtering.
- Never let the audit path see a tool's signature/description/params — only `key` and `score`.
- Let both audit trails be read back as paginated, filterable, human-readable tables via `mcc audit tool` / `mcc audit search`.
- Keep the two trails independently toggleable, matching the existing opt-in-by-empty-string convention.

**Non-Goals:**
- No redaction/toggle setting for search query text (unlike `audit_params` for tool-call params) — query text is the feature, not an optional extra, and search queries carry materially lower sensitivity than arbitrary tool call parameters (shell commands, URLs with embedded credentials, etc.).
- No unified audit index / event-type discriminator across tool-call and search audit.
- No hook-based event system (`on_search_call`) for search — see Decisions.
- No REST endpoint for search auditing or for reading audit logs — CLI only, matching the CLI-only surface `mcc user`/`mcc tool` already have (`/admin/*` HTTP routes are a separate, not-yet-built idea in `docs/future-features.md` and out of scope here).

## Decisions

**Separate `SearchAuditIndex`, not a unified audit index with a type field.**
A single index with an `event_type` discriminator would let the CLI query one source and would avoid two on/off settings. Rejected because it makes the mapping worse for both record types (tool-call fields like `duration_ms`/`status` are meaningless on a search record and vice versa — every document would carry a pile of null fields), and the CLI cost of querying two indices and merging client-side is trivial at these volumes (page size ≤ a few hundred, sorted by timestamp, no cross-index joins needed). Two indices, two settings, two mappings — each stays exactly as clean as `AuditIndex` is today.

**Direct call from `search()`, not an `on_search_call` hook mirroring `on_tool_call`.**
`on_tool_call` exists because tool calls have two independent consumers today (logging, Prometheus metrics) plus audit as a third, all needing to fire from the one `ToolModel.call()` chokepoint regardless of transport. `search()` has exactly one call site and, as of this change, exactly one consumer of a "search happened" event (the audit write). A hook registry for a single producer and single consumer is indirection with no second caller to justify it — CLAUDE.md's "no speculative abstractions." If a second consumer (metrics, a future `/search` route) shows up later, introducing the hook at that point is a small, well-motivated change.

**`search()` computes the RBAC-filtered `(tool, score)` list once, shared by the audit call and the response.**
Today `search()` builds `accessible` as already-formatted `f"[{score:.2f}]\n{tool.signature}"` strings in one comprehension. Refactoring to first compute `allowed = [(tool, score) for tool, score in results if tool.allows(user)]`, then deriving both the audit payload (`[(tool.key, score) for tool, score in allowed]`) and the response text from `allowed`, guarantees the audit path is structurally incapable of seeing `tool.signature` — it's not in scope at the point the audit call is made, rather than "trust the audit function to only pick two fields off a richer object."

**`results` field serialized as `"key=score;key=score"` text, reusing `AuditIndex._serialize_params`'s exact separator convention.**
Same rationale as the existing code: human/grep-readable, not meant for structured querying inside the field. Consistency with the sibling index beats inventing a second convention (e.g. `key:score`) in the same file.

**`IndexBase.search()` gains `limit`/`offset`/`sort`, renaming `size`→`limit`, on both backends.**
Needed regardless of search-audit specifically — today's `search(query, size=10000)` has no sort and no pagination, so a CLI "give me the last 20" is impossible without pulling up to 10000 docs and sorting/slicing in Python. `limit`/`offset` names match the CLI's own `--limit`/`--offset` flags directly (rather than `size`/`from_`, ES/OS's native param names, which would leak backend vocabulary into the CLI). Both `mcc/db/es.py` and `mcc/db/os.py` change together since either can be the active `SEARCH_BACKEND`; existing callers passing `size=` are updated to `limit=`.

**Two CLI subcommands (`mcc audit tool`, `mcc audit search`), not one `mcc audit log --type`.**
Falls directly out of the separate-index decision — each subcommand's filters and columns are shape-specific (`--tool-key` + Status/Duration/Params vs. `--query` + MinScore/Results), and a single command would need to conditionally render different columns depending on `--type` anyway. Two subcommands sharing a small query+render helper is simpler than one command branching internally.

**Filters (`--user`, `--since`, plus `--tool-key`/`--query`) are in scope now, not deferred.**
An audit log with only offset/limit paging over an unfiltered stream is of limited practical use the moment there's more than a handful of records — "what did alice run last week" is the actual workflow this is for.

## Risks / Trade-offs

- **[Risk]** The `audit_index` → `audit_tool_index` rename is breaking for any deployment that already set it. → **Mitigation**: it's a rename, not a removal — call it out explicitly in the proposal's Impact section and in the settings file's comment; no code-level migration is possible since a settings *name* isn't something the app can shim without keeping the old key alive indefinitely, which the project's "no backwards-compatibility shims" convention rules out.
- **[Risk]** `IndexBase.search()`'s signature change (`size` → `limit`) breaks any existing call site still passing `size=`. → **Mitigation**: grep every call site as part of implementation (tasks.md) and update them in the same change; this is a small, fully-owned surface (two backend files, a handful of callers), not a public API.
- **[Risk]** Two independent audit indices means an operator wanting "one audit log" has to enable and query two things. → **Mitigation**: accepted trade-off per the Decisions section above; both settings default off, and enabling either is a one-line settings change.

## Migration Plan

1. Ship the setting rename and new setting together; document the rename in the settings file comment.
2. No data migration needed — `audit_tool_index` and `audit_search_index` are fresh index names (or the same value as the old `audit_index`, an operator's choice); no existing audit documents need transformation.
3. Rollback is a plain revert — nothing external depends on the new index/CLI surface yet.
