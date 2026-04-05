## Why

TinyDB stores users in a local JSON file, which is not viable in production: no replication, no durability guarantees, and the file is tied to the process host. Elasticsearch is already in the stack and is a natural fit — users are simple documents with no relational needs, just CRUD and two lookup patterns (by username and by email).

## What Changes

- New `UserModel` Pydantic model in `mcc/auth/models.py` replaces raw user dicts throughout the codebase.
- `mcc/auth/db.py` is rewritten: all functions become async, backed by `AsyncElasticsearch` instead of TinyDB. `username` is used as the ES document `_id`.
- All callers updated to `await` db calls and use `UserModel` attribute access instead of dict-style access.
- `mcc/cli.py` wraps async db calls with `asyncio.run()`.
- `settings.yaml` gains an `elasticsearch` config block (host, port, index, optional credentials); `users_db` removed.
- Index initialization exposed as `mcc index create` / `mcc index delete` CLI commands.
- `tinydb` removed from dependencies; `elasticsearch[async]` added.

## Capabilities

### New Capabilities
- `elasticsearch-user-store`: AsyncElasticsearch-backed user CRUD with explicit index mapping and UserModel

### Modified Capabilities
- `user-store`: replaced by `elasticsearch-user-store`
- `admin-cli`: new `mcc index` command group; all user commands updated for async
- `bearer-auth-middleware`: no functional change, updated to use UserModel attributes
- `execute-tool`: `can_access` signature updated to `UserModel | None`
- `search-tool`: same

## Impact

- `mcc/auth/models.py` — new file: `UserModel(BaseModel)`
- `mcc/auth/db.py` — complete rewrite: async ES client, all functions async
- `mcc/auth/util.py` — dict access → attribute access; `can_access(UserModel | None, ...)`
- `mcc/auth/dangerous.py` — async; fix latent `user["group"]` bug → `user.groups`
- `mcc/app.py` — attribute access on UserModel
- `mcc/cli.py` — `asyncio.run()` wrappers; new `index` command group
- `mcc/settings.yaml` — `elasticsearch` block replaces `users_db`
- `pyproject.toml` — `tinydb` → `elasticsearch[async]`
- `tests/test_auth.py` — UserModel instances in assertions; async truncate fixture
