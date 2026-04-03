## 1. auth.py — Refactor user store

- [x] 1.1 Remove `generate_token`, `hash_token`, `get_user_by_token` functions
- [x] 1.2 Update schema: `create_user(username, email=None, groups=None, tools=None)` — store both fields, raise on duplicate username or duplicate email
- [x] 1.3 Update `delete_user`, `add_group`, `remove_group`, `add_tool`, `remove_tool` to key by `username`
- [x] 1.4 Keep `get_user_by_email(email)` for email-based lookup
- [x] 1.5 Add `get_user_by_username(username)` for username-based lookup
- [x] 1.6 Update `list_users` — no `token_hash` field, return `username` + `email` (if present)
- [x] 1.7 Update `get_current_user(ctx)`: try email first → `get_user_by_email`, then fall back to `claims["login"]` → `get_user_by_username`

## 2. app.py — Wire GitHubProvider, remove middleware

- [x] 2.1 Remove `mcp.add_middleware(BearerAuthMiddleware)` and its import
- [x] 2.2 Read `MCC_GITHUB_CLIENT_ID`, `MCC_GITHUB_CLIENT_SECRET`, `MCC_BASE_URL` from env; raise `RuntimeError` if any are missing
- [x] 2.3 Set `mcp.auth = GitHubProvider(client_id=..., client_secret=..., base_url=...)`
- [x] 2.4 Update `search` and `execute` tools to use `await get_current_user(ctx)`

## 3. middleware.py — Delete

- [x] 3.1 Delete `mcc/middleware.py`

## 4. mcc/tools.yaml — Update admin tools

- [x] 4.1 Replace `get_user_by_name` entry with `get_user_by_username` and add `get_user_by_email`

## 5. cli.py — Username + optional email commands

- [x] 5.1 Update `add-user`: `--username` / `-u` required, `--email` / `-e` optional; remove token output
- [x] 5.2 Update `remove-user`, `grant`, `revoke`: argument is `username`
- [x] 5.3 Update `list-users`: show `username` and `email` (if present)
- [x] 5.4 Update error messages to reference username

## 6. Tests

- [x] 6.1 Update auth tests: use username-keyed fixtures, test `create_user` with and without email, test duplicate email raises
- [x] 6.2 Update `get_current_user` tests: email-match, username-fallback, email-takes-precedence, unauthenticated, no record
