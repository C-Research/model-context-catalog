## ADDED Requirements

### Requirement: Admin-gated user listing
The server SHALL expose a `GET /users` HTTP route, gated via `@route(admin=True)`, that lists all users via the existing `list_users()` function.

#### Scenario: Non-admin request rejected
- **WHEN** a `GET /users` request arrives without a valid API key resolving to an admin user
- **THEN** the server responds `401` and no user data is returned

#### Scenario: Admin request returns all users
- **WHEN** a `GET /users` request arrives with a valid API key resolving to a user in the `admin` group
- **THEN** the server responds `200` with every user returned by `list_users()`

### Requirement: Key metadata is omitted by default
`GET /users` SHALL omit each user's `.key` field from the response by default. `GET /users?keys=true` SHALL include it, exactly as returned by `list_users()` (`{"prefix", "created_at", "expires_at"}`, never the hash or raw key).

#### Scenario: Default response omits key metadata
- **WHEN** a `GET /users` request arrives with no `keys` query parameter, or `keys=false`
- **THEN** no user object in the response contains a `key` field

#### Scenario: keys=true includes key metadata
- **WHEN** a `GET /users?keys=true` request arrives
- **THEN** each user object that has an API key includes a `key` field with `prefix`, `created_at`, and `expires_at`, and never a `hash` or raw key value
