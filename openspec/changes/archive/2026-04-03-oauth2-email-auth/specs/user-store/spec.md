## MODIFIED Requirements

### Requirement: TinyDB user document schema
The user store SHALL use TinyDB with a single `users` table. Each document SHALL contain: `username` (string, unique — GitHub login handle), `email` (string or null, unique when present), `groups` (list of strings), `tools` (list of strings). The fields `token_hash` and `is_admin` SHALL NOT be present.

#### Scenario: User document has required fields
- **WHEN** a user is created with username `"alice"` and email `"alice@example.com"`
- **THEN** the stored document contains `username`, `email`, `groups`, and `tools` fields

#### Scenario: User document without email
- **WHEN** a user is created with username `"alice"` and no email
- **THEN** the stored document contains `username`, `groups`, and `tools`; `email` is `None` or absent

#### Scenario: groups and tools default to empty lists
- **WHEN** a user is created without specifying groups or tools
- **THEN** `groups` is `[]` and `tools` is `[]`

#### Scenario: User document contains no token fields
- **WHEN** a user is created
- **THEN** the stored document does NOT contain `token_hash`

## REMOVED Requirements

### Requirement: Token hashing
**Reason**: Tokens are issued and validated by the OAuth2 provider. MCC no longer generates or stores tokens.
**Migration**: Remove calls to `generate_token`, `hash_token`, and `get_user_by_token`.

## MODIFIED Requirements

### Requirement: User CRUD operations
The user store SHALL expose functions: `create_user(username, email=None, groups=None, tools=None)`, `delete_user(username)`, `get_user_by_username(username) -> dict | None`, `get_user_by_email(email) -> dict | None`, `list_users() -> list[dict]`, `add_group(username, group)`, `remove_group(username, group)`, `add_tool(username, tool)`, `remove_tool(username, tool)`. The functions `get_user_by_token`, `generate_token`, and `hash_token` SHALL be removed.

#### Scenario: create_user stores record by username
- **WHEN** `create_user("alice")` is called
- **THEN** a user document with `username="alice"` is inserted into TinyDB

#### Scenario: create_user stores email when provided
- **WHEN** `create_user("alice", email="alice@example.com")` is called
- **THEN** the stored document has `email="alice@example.com"`

#### Scenario: Duplicate username raises error
- **WHEN** `create_user` is called with a username that already exists
- **THEN** a `ValueError` is raised

#### Scenario: Duplicate email raises error
- **WHEN** `create_user` is called with an email that is already stored on another user
- **THEN** a `ValueError` is raised

#### Scenario: delete_user removes the document by username
- **WHEN** `delete_user("alice")` is called
- **THEN** the user document is removed from TinyDB

#### Scenario: delete_user on nonexistent username raises error
- **WHEN** `delete_user` is called with a username not in the store
- **THEN** a `ValueError` is raised

#### Scenario: get_user_by_username returns user dict
- **WHEN** `get_user_by_username("alice")` is called and the user exists
- **THEN** the returned dict contains `username`, `groups`, and `tools`

#### Scenario: get_user_by_username returns None for unknown username
- **WHEN** `get_user_by_username` is called with a username not in the store
- **THEN** it returns `None`

#### Scenario: get_user_by_email returns user dict
- **WHEN** `get_user_by_email("alice@example.com")` is called and a user with that email exists
- **THEN** the returned dict contains `username`, `email`, `groups`, and `tools`

#### Scenario: get_user_by_email returns None for unknown email
- **WHEN** `get_user_by_email` is called with an email not in the store
- **THEN** it returns `None`

#### Scenario: add_group, remove_group, add_tool, remove_tool keyed by username
- **WHEN** `add_group("alice", "ops")` is called
- **THEN** `"ops"` is in alice's `groups` list

#### Scenario: add_group on already-member is a no-op
- **WHEN** `add_group` is called for a group the user already has
- **THEN** no duplicate is added and no error is raised

#### Scenario: remove_group on nonexistent group raises error
- **WHEN** `remove_group("alice", "ops")` is called and alice is not in `ops`
- **THEN** a `ValueError` is raised
