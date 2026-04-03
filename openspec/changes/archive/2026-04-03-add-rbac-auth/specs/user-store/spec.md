## ADDED Requirements

### Requirement: TinyDB user document schema
The user store SHALL use TinyDB with a single `users` table. Each document SHALL contain: `username` (string, unique), `token_hash` (string, `sha256:<hex>`), `is_admin` (boolean), `groups` (list of strings), `tools` (list of strings). No other top-level keys are permitted in user documents.

#### Scenario: User document has required fields
- **WHEN** a user is created with username `"alice"`, a token, and `is_admin=False`
- **THEN** the stored document contains `username`, `token_hash`, `is_admin`, `groups`, and `tools` fields

#### Scenario: groups and tools default to empty lists
- **WHEN** a user is created without specifying groups or tools
- **THEN** `groups` is `[]` and `tools` is `[]`

### Requirement: Token hashing
Tokens SHALL be generated as 32-byte (64 hex character) random strings. Tokens SHALL be stored as `sha256:<lowercase hex digest>`. The plain token SHALL never be written to the database.

#### Scenario: Token is hashed before storage
- **WHEN** a user is created with a generated token
- **THEN** the stored `token_hash` is the SHA-256 hex digest of the token prefixed with `sha256:`

#### Scenario: Token lookup by hash
- **WHEN** a bearer token is presented
- **THEN** it is hashed and compared against `token_hash` values in TinyDB to find the matching user

### Requirement: User CRUD operations
The user store SHALL expose functions: `create_user(username, is_admin) -> token`, `delete_user(username)`, `get_user_by_token(token) -> dict | None`, `get_user_by_name(username) -> dict | None`, `add_group(username, group)`, `remove_group(username, group)`, `add_tool(username, tool)`, `remove_tool(username, tool)`.

#### Scenario: create_user returns plain token once
- **WHEN** `create_user("alice", is_admin=False)` is called
- **THEN** the function returns the plain token string and stores only the hash

#### Scenario: Duplicate username raises error
- **WHEN** `create_user` is called with a username that already exists
- **THEN** a `ValueError` is raised

#### Scenario: delete_user removes the document
- **WHEN** `delete_user("alice")` is called
- **THEN** the user document is removed from TinyDB

#### Scenario: delete_user on nonexistent user raises error
- **WHEN** `delete_user` is called with a username not in the store
- **THEN** a `ValueError` is raised

#### Scenario: get_user_by_token returns user without token_hash
- **WHEN** `get_user_by_token(token)` is called with a valid token
- **THEN** the returned dict contains `username`, `is_admin`, `groups`, `tools` but NOT `token_hash`

#### Scenario: get_user_by_token returns None for unknown token
- **WHEN** `get_user_by_token` is called with a token not in the store
- **THEN** it returns `None`

#### Scenario: add_group appends group to user
- **WHEN** `add_group("alice", "ops")` is called
- **THEN** `"ops"` is in `alice`'s `groups` list

#### Scenario: add_group on already-member is a no-op
- **WHEN** `add_group` is called for a group the user already has
- **THEN** no duplicate is added and no error is raised

#### Scenario: remove_group on nonexistent group raises error
- **WHEN** `remove_group("alice", "ops")` is called and alice is not in `ops`
- **THEN** a `ValueError` is raised

#### Scenario: add_tool and remove_tool mirror group behavior
- **WHEN** `add_tool("alice", "special_tool")` is called
- **THEN** `"special_tool"` is in alice's `tools` list
- **WHEN** `remove_tool("alice", "special_tool")` is called
- **THEN** `"special_tool"` is removed from alice's `tools` list
