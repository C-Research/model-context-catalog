## MODIFIED Requirements

### Requirement: Auth provider wired as mcp.auth
The system SHALL configure `mcp.auth` with a provider instance returned by `get_provider()` in `mcc/auth/backend.py`. The provider is determined by `settings.auth`. For proxy providers (`github`, `google`, etc.), credentials SHALL be read from the `oauth:` settings block (or `MCC_OAUTH__*` env vars). For the `jwt` backend, config SHALL be read from the `jwt:` settings block (or `MCC_JWT__*` env vars). `get_provider()` SHALL return `None` for `dev-admin` and `dev-public`, in which case `mcp.auth` SHALL not be set.

#### Scenario: Server starts with google backend configured
- **WHEN** `auth: "google"` and `MCC_OAUTH__CLIENT_ID`, `MCC_OAUTH__CLIENT_SECRET`, `MCC_OAUTH__BASE_URL` are set
- **THEN** `mcp.auth` is a `GoogleProvider` instance

#### Scenario: Server starts with jwt backend configured
- **WHEN** `auth: "jwt"` and `MCC_JWT__JWKS_URI`, `MCC_JWT__ISSUER`, `MCC_JWT__AUDIENCE`, `MCC_JWT__AUTHORIZATION_SERVER`, `MCC_JWT__BASE_URL` are set
- **THEN** `mcp.auth` is a `RemoteAuthProvider` instance

#### Scenario: Server starts with dev-admin (no provider)
- **WHEN** `auth: "dev-admin"`
- **THEN** `get_provider()` returns `None` and `mcp.auth` is not set

#### Scenario: Missing required oauth settings raises at startup
- **WHEN** `auth: "github"` and `MCC_OAUTH__CLIENT_ID` is unset
- **THEN** provider construction raises before accepting connections (TypeError from FastMCP provider constructor)

### Requirement: get_current_user resolves token identity to UserModel
The system SHALL provide an async `get_current_user()` in `mcc/auth/util.py`. For OAuth/JWT backends it SHALL call `get_access_token()` to retrieve the token, then resolve identity in order:
1. If `claims["email"]` is non-null, call `get_user_by_email(email)` — return the user if found
2. Fall back to `claims["login"]` if present, call `get_user_by_username(login)` — return the user if found
3. Return `None` if no token, no matching record, or all identity claims absent

#### Scenario: User resolves via email claim
- **WHEN** `get_current_user()` is called and `claims["email"]` is non-null and matches a user record
- **THEN** it returns that UserModel

#### Scenario: User resolves via login claim (GitHub)
- **WHEN** `get_current_user()` is called, `claims["email"]` is null, and `claims["login"]` matches a user record
- **THEN** it returns that UserModel

#### Scenario: Email match takes precedence over login
- **WHEN** both `claims["email"]` and `claims["login"]` match different records
- **THEN** the record matched by email is returned

#### Scenario: Unauthenticated request returns None
- **WHEN** `get_current_user()` is called with no active access token
- **THEN** it returns `None`

#### Scenario: No matching record returns None
- **WHEN** neither email nor login match any stored user
- **THEN** `get_current_user()` returns `None`

## REMOVED Requirements

### Requirement: GitHubProvider wired as mcp.auth
**Reason:** Replaced by the generic `get_provider()` dispatch in `backend.py`. GitHub is still supported via `auth: "github"` but is no longer the only wired provider.
**Migration:** Set `auth: "github"` and move credentials to the `oauth:` settings block.

## ADDED Requirements

### Requirement: oauth settings block replaces provider-specific blocks
The `oauth:` settings block SHALL be the single source of credentials for all OAuthProxy providers. The old `github_oauth:` and `github_pat:` blocks SHALL be removed from `settings.yaml`.

#### Scenario: github provider reads from oauth block
- **WHEN** `auth: "github"` and `settings.oauth.client_id`, `settings.oauth.client_secret`, `settings.oauth.base_url` are set
- **THEN** `GitHubProvider` is instantiated with those values

#### Scenario: google provider reads from oauth block
- **WHEN** `auth: "google"` and `settings.oauth.client_id`, `settings.oauth.client_secret`, `settings.oauth.base_url` are set
- **THEN** `GoogleProvider` is instantiated with those values

### Requirement: jwt settings block for OIDC configuration
The `jwt:` settings block SHALL hold all configuration for the generic OIDC backend: `jwks_uri`, `issuer`, `audience`, `authorization_server`, `base_url`, and optionally `required_scopes`.

#### Scenario: jwt settings available as MCC_JWT__* env vars
- **WHEN** `MCC_JWT__JWKS_URI` is set in the environment
- **THEN** it overrides `settings.jwt.jwks_uri`

### Requirement: No-record users can access public group tools
When `get_current_user` returns `None`, `can_access` SHALL still return `True` for tools in the `public` group.

#### Scenario: Unprovisioned user can call public tools
- **WHEN** an authenticated user has no matching MCC user record and calls a tool in the `public` group
- **THEN** the call succeeds

#### Scenario: Unprovisioned user cannot call non-public tools
- **WHEN** an authenticated user has no matching MCC user record and calls a tool not in the `public` group
- **THEN** the call returns `"Unauthorized"`
