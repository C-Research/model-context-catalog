## 1. Dependencies and config

- [x] 1.1 Replace `tinydb` with `elasticsearch[async]` in `pyproject.toml` dependencies
- [x] 1.2 Remove `users_db` from `mcc/settings.yaml`; add `elasticsearch` block: `host`, `port`, `scheme`, `index`, `username`, `password`
- [x] 1.3 Remove `users_db` from `settings.local.yaml` if present; add `elasticsearch` block for local dev

## 2. UserModel (`mcc/auth/models.py`)

- [x] 2.1 Create `mcc/auth/models.py` with `UserModel(BaseModel)`: `username: str`, `email: str | None`, `groups: list[str]`, `tools: list[str]`

## 3. ES user store (`mcc/auth/db.py`)

- [x] 3.1 Rewrite `mcc/auth/db.py`: remove TinyDB imports; add `AsyncElasticsearch` client factory `_get_client()` and `_index()` helper from settings
- [x] 3.2 Add `_UsersTable` class with `async truncate()` and no-op `clear_cache()`; export module-level `users = _UsersTable()` for test compatibility
- [x] 3.3 Implement `async create_user(username, email, tools, groups)` — index with `_id=username`, term query for email uniqueness, both raise `ValueError` on conflict
- [x] 3.4 Implement `async delete_user(username)` — `client.delete(_id=username)`, raise `ValueError` on 404
- [x] 3.5 Implement `async list_users() -> list[UserModel]` — `match_all` search, return list of `UserModel`
- [x] 3.6 Implement `async get_user_by_username(username) -> UserModel | None` — `client.get(_id=username)`
- [x] 3.7 Implement `async get_user_by_email(email) -> UserModel | None` — `term` query on `email` keyword field
- [x] 3.8 Implement `async add_group(username, group)` — get → mutate → index, idempotent
- [x] 3.9 Implement `async remove_group(username, group)` — get → mutate → index, raise `ValueError` if not member
- [x] 3.10 Implement `async add_tool(username, tool)` — get → mutate → index, idempotent
- [x] 3.11 Implement `async remove_tool(username, tool)` — get → mutate → index, raise `ValueError` if not present
- [x] 3.12 All writes pass `refresh=True`

## 4. Update callers

- [x] 4.1 Update `mcc/auth/util.py`: `can_access(user: UserModel | None, ...)` — replace all `user["..."]` with `user.field` attribute access; `await` all db calls in `get_current_user` and `list_tools`
- [x] 4.2 Update `mcc/auth/dangerous.py`: make `get_user_context` async; fix `user["group"]` bug → `user.groups`; `await list_users()`
- [x] 4.3 Update `mcc/app.py`: replace `user["username"]` / `user.get("email")` with `user.username` / `user.email`
- [x] 4.4 Update `mcc/cli.py`: wrap every async db call (`create_user`, `delete_user`, `list_users`, `add_group`, `remove_group`, `add_tool`, `remove_tool`) in `asyncio.run()`

## 5. Index CLI (`mcc/cli.py`)

- [x] 5.1 Add `mcc index` command group to CLI
- [x] 5.2 Implement `mcc index create` — creates ES index with explicit keyword mapping for `username`, `email`, `groups`, `tools`; idempotent (no-op if exists)
- [x] 5.3 Implement `mcc index delete` — deletes ES index; confirm before executing

## 6. Tests

- [x] 6.1 Update `tests/test_auth.py` fixture: make `_fresh_db` async with `@pytest_asyncio.fixture`, call `await users.truncate()`
- [x] 6.2 Update `TestCanAccess`: replace `user = {"username": ..., "groups": [...], "tools": [...]}` dict construction with `UserModel(username=..., groups=[...])` instances
- [x] 6.3 Update any `user["field"]` assertions throughout test file to `user.field`
- [x] 6.4 `elasticsearch[async]` already in main deps; `pytest_asyncio` already in dev deps
