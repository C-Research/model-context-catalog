## ADDED Requirements

### Requirement: GitHubProvider wired as mcp.auth
The system SHALL configure `mcp.auth` with a `GitHubProvider` instance. `MCC_GITHUB_CLIENT_ID`, `MCC_GITHUB_CLIENT_SECRET`, and `MCC_BASE_URL` SHALL be read from environment variables at startup. No `BearerAuthMiddleware` SHALL be registered.

#### Scenario: Server starts with GitHubProvider configured
- **WHEN** the MCP server starts with `MCC_GITHUB_CLIENT_ID`, `MCC_GITHUB_CLIENT_SECRET`, and `MCC_BASE_URL` set
- **THEN** `mcp.auth` is a `GitHubProvider` instance and no `BearerAuthMiddleware` is present

#### Scenario: Missing required env vars raises at startup
- **WHEN** any of `MCC_GITHUB_CLIENT_ID`, `MCC_GITHUB_CLIENT_SECRET`, or `MCC_BASE_URL` is unset
- **THEN** the server raises a `RuntimeError` before accepting connections

### Requirement: get_current_user resolves GitHub identity to user dict
The system SHALL provide a `get_current_user(ctx)` async helper in `auth.py`. It SHALL call `get_access_token()` and resolve identity using the following order:
1. If `claims["email"]` is non-null, call `get_user_by_email(email)` — return the user if found
2. Fall back to `claims["login"]` (GitHub handle), call `get_user_by_username(login)` — return the user if found
3. Return `None` if no token, no matching record, or both claims absent

#### Scenario: User with public email resolves via email
- **WHEN** `get_current_user(ctx)` is called and `claims["email"]` is non-null and matches a user record
- **THEN** it returns that user dict

#### Scenario: User without public email resolves via username
- **WHEN** `get_current_user(ctx)` is called, `claims["email"]` is null, and `claims["login"]` matches a user record
- **THEN** it returns that user dict

#### Scenario: Email match takes precedence over username
- **WHEN** `get_current_user(ctx)` is called and both email and login match different records
- **THEN** it returns the record matched by email

#### Scenario: Unauthenticated request returns None
- **WHEN** `get_current_user(ctx)` is called with no active access token
- **THEN** it returns `None`

#### Scenario: No matching record returns None
- **WHEN** neither email nor username match any stored user
- **THEN** `get_current_user` returns `None`

### Requirement: No-record users can access public group tools
When `get_current_user` returns `None`, `can_access` SHALL still return `True` for tools in the `public` group.

#### Scenario: Unprovisioned GitHub user can call public tools
- **WHEN** an authenticated GitHub user has no matching MCC user record and calls a tool in the `public` group
- **THEN** the call succeeds

#### Scenario: Unprovisioned GitHub user cannot call non-public tools
- **WHEN** an authenticated GitHub user has no matching MCC user record and calls a tool not in the `public` group
- **THEN** the call returns `"Unauthorized"`
