## Context

TinyDB is a file-backed document store. The migration to Elasticsearch replaces it with a self-hosted cluster using the official `elasticsearch[async]` Python client (`AsyncElasticsearch`). The user document schema is unchanged — username, email, groups, tools — but is now represented as a Pydantic model and stored in an ES index with an explicit keyword mapping.

The entire `mcc/auth/db.py` public interface becomes async. Since the MCP path (`app.py`, `util.py`) is already async, this is a clean fit. The CLI is sync-at-the-boundary and wraps each db call in `asyncio.run()`.

## Goals / Non-Goals

**Goals:**
- Drop TinyDB, zero file-based user storage
- All db operations async via `AsyncElasticsearch`
- `UserModel` is the single representation of a user throughout the codebase
- Explicit ES index mapping (all fields `keyword`)
- Index lifecycle managed via `mcc index` CLI commands
- Self-hosted connection config (host, port, optional basic auth)

**Non-Goals:**
- Elastic Cloud / API key auth (not needed for self-hosted)
- User search / filtering beyond username and email lookup
- Audit logging
- Token-level caching or connection pooling beyond ES client defaults

## Decisions

### `UserModel` in `mcc/auth/models.py`

```python
class UserModel(BaseModel):
    username: str
    email: str | None = None
    groups: list[str] = []
    tools: list[str] = []
```

Lives in `mcc/auth/models.py`, mirroring how `ToolModel` lives in `mcc/models.py`. Imported by `db.py`, `util.py`, `dangerous.py`, `app.py`, `cli.py`, and tests.

All callers that previously used `user["groups"]` etc. move to `user.groups`. `can_access` signature becomes `(user: UserModel | None, tool: ToolModel) -> bool`.

### `username` as ES `_id`

`username` is the natural primary key and is used as the ES document `_id`:
- `create_user` → `client.index(_id=username, ...)` — 409 on duplicate (converted to `ValueError`)
- `get_user_by_username` → `client.get(_id=username)` — O(1), no search query
- `delete_user` → `client.delete(_id=username)` — 404 on missing (converted to `ValueError`)

Email uniqueness is still enforced at the application layer via a `term` query before insert. ES does not natively enforce secondary uniqueness.

### All writes use `refresh=True`

ES defaults to a 1-second async refresh. All write operations (`index`, `delete`, `update`, `delete_by_query`) pass `refresh=True` to make changes immediately visible to subsequent reads. Required for correctness in the CLI and tests.

### Update pattern: read → mutate → full replace

`add_group`, `remove_group`, `add_tool`, `remove_tool` all follow:
1. `client.get(_id=username)` → build `UserModel`
2. Mutate the model in memory
3. `client.index(_id=username, document=model.model_dump(), refresh=True)`

ES partial `update()` is not used — full replace is simpler and we always read first anyway.

### Connection factory

A module-level `_get_client()` function returns a singleton `AsyncElasticsearch` instance built from `settings.ELASTICSEARCH`. Config fields: `host`, `port`, `scheme` (default `"http"`), `username`, `password` (both optional). If username is set, basic auth is wired in.

```python
def _get_client() -> AsyncElasticsearch:
    cfg = settings.ELASTICSEARCH
    kwargs = {"hosts": [f"{cfg.SCHEME}://{cfg.HOST}:{cfg.PORT}"]}
    if cfg.USERNAME:
        kwargs["basic_auth"] = (cfg.USERNAME, cfg.PASSWORD)
    return AsyncElasticsearch(**kwargs)
```

### Explicit index mapping

```json
{
  "mappings": {
    "properties": {
      "username": { "type": "keyword" },
      "email":    { "type": "keyword" },
      "groups":   { "type": "keyword" },
      "tools":    { "type": "keyword" }
    }
  }
}
```

All fields are `keyword` — exact-match only. ES would auto-map strings as `text` + `keyword` subfield by default; explicit mapping avoids the `text` analysis overhead and keeps queries clean.

### `mcc index` CLI commands

```
mcc index create   → creates the index with the mapping above (no-op if exists)
mcc index delete   → deletes the index (prompts for confirmation)
```

Operator-controlled, intentional schema management. No auto-creation on startup — prod environments should have the index pre-created before the server starts.

**Exception**: `mcc index create` is idempotent (uses `ignore=400` / check-then-create) so it is safe to run in automation.

### Test infrastructure

`mcc/auth/db.py` exposes a module-level `users` object with `async def truncate()` and `def clear_cache()` (no-op) to preserve the existing test fixture interface:

```python
class _UsersTable:
    async def truncate(self):
        await _get_client().delete_by_query(
            index=_index(), body={"query": {"match_all": {}}}, refresh=True
        )
    def clear_cache(self): pass

users = _UsersTable()
```

The test fixture becomes:
```python
@pytest.fixture(autouse=True)
async def _fresh_db():
    await users.truncate()
    yield
    await users.truncate()
```

Tests that construct `user` dicts for `can_access` assertions are updated to construct `UserModel` instances instead.

## Risks / Trade-offs

- **ES must be running**: unlike TinyDB (always available), ES requires an external service. Dev setups need docker-compose or similar. Mitigation: document clearly; keep `dangerous` auth backend for local dev.
- **`refresh=True` cost**: forcing immediate refresh on every write has a small performance cost. Acceptable — user management is low-frequency CLI/admin traffic, not hot path.
- **No transactions**: `add_group` read→write is not atomic. Two concurrent CLI invocations could race. Acceptable — user management is CLI-driven and inherently low concurrency.
- **Email uniqueness race**: two concurrent `create_user` calls with the same email could both pass the pre-check and insert. Mitigation: same limitation existed with TinyDB; document as a known constraint.
