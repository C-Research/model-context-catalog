## 1. Dependencies and project setup

- [x] 1.1 Add `tinydb` and `click` to `pyproject.toml` dependencies
- [x] 1.2 Add `mcc = "mcc.cli:cli"` to `[project.scripts]` in `pyproject.toml`

## 2. User store (`mcc/auth.py`)

- [x] 2.1 Create `mcc/auth.py` with TinyDB setup (db path configurable, default `users.db`)
- [x] 2.2 Implement token generation (32-byte random hex) and `hash_token(token) -> str` (sha256: prefix)
- [x] 2.3 Implement `create_user(username, is_admin) -> token` — raises `ValueError` on duplicate username
- [x] 2.4 Implement `delete_user(username)` — raises `ValueError` if not found
- [x] 2.5 Implement `get_user_by_token(token) -> dict | None` — returns user without `token_hash`
- [x] 2.6 Implement `get_user_by_name(username) -> dict | None`
- [x] 2.7 Implement `add_group(username, group)` — no-op if already member
- [x] 2.8 Implement `remove_group(username, group)` — raises `ValueError` if not member
- [x] 2.9 Implement `add_tool(username, tool)` — no-op if already present
- [x] 2.10 Implement `remove_tool(username, tool)` — raises `ValueError` if not present
- [x] 2.11 Implement `can_access(user, tool_name, tool_entry) -> bool` — public group bypass, group membership, explicit tool check

## 3. Bearer auth middleware (`mcc/middleware.py`)

- [x] 3.1 Create `mcc/middleware.py` with `BearerAuthMiddleware(Middleware)`
- [x] 3.2 Implement `on_initialize`: extract `Authorization` header via `get_http_request()`, strip `Bearer ` prefix, call `get_user_by_token`, store result in `ctx.set_state("current_user", user)` (None if missing/invalid)

## 4. CLI (`mcc/cli.py`)

- [x] 4.1 Create `mcc/cli.py` with Click group `cli`
- [x] 4.2 Implement `add-user <username> [--admin]` — calls `create_user`, prints token with save warning
- [x] 4.3 Implement `remove-user <username>` — calls `delete_user`, exits non-zero on error
- [x] 4.4 Implement `grant <username> [--group] [--tool]` — requires at least one option, calls `add_group`/`add_tool`
- [x] 4.5 Implement `revoke <username> [--group] [--tool]` — requires at least one option, calls `remove_group`/`remove_tool`

## 5. RBAC in app (`mcc/app.py`)

- [x] 5.1 Update `execute` to accept `ctx: Context`, call `ctx.get_state("current_user")`, run `can_access` check, return `"Unauthorized"` if denied
- [x] 5.2 Update `search` to accept `ctx: Context`, call `ctx.get_state("current_user")`, filter `loader.items()` through `can_access` before query matching

## 6. Wire up (`main.py`)

- [x] 6.1 Register `BearerAuthMiddleware` on the FastMCP app instance in `main.py`
