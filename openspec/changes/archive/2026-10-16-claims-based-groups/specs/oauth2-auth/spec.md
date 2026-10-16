## MODIFIED Requirements

### Requirement: get_current_user resolves token identity to UserModel
The system SHALL provide an async `get_current_user()` in `mcc/auth/util.py`. For OAuth/JWT backends it SHALL call `get_access_token()` to retrieve the token, then resolve identity in order:
1. If `claims["email"]` is non-null, lowercase it and call `get_user_by_email(email)` — use the user if found
2. Otherwise (or if no record matched) fall back to `claims["login"]` if present, call `get_user_by_username(login)` — use the user if found
3. If `claims.roles_claim` is configured, derive groups from the token's roles per the `claims-based-groups` capability and union them with the matched record's groups, or build a claims-only user when no record matched but groups were derived
4. Return `None` if there is no token, or no record matched and no groups were derived

A failure of the user-store lookup SHALL NOT make the request anonymous when claim-derived groups are available.

#### Scenario: User resolves via email claim
- **WHEN** `get_current_user()` is called and `claims["email"]` is non-null and matches a user record (case-insensitively)
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

#### Scenario: No matching record and no claim groups returns None
- **WHEN** neither email nor login match any stored user and no groups are derived from claims
- **THEN** `get_current_user()` returns `None`

#### Scenario: No record but claim groups present
- **WHEN** no record matches, `claims.roles_claim` is configured, and the token's roles derive at least one group
- **THEN** `get_current_user()` returns a claims-derived UserModel

### Requirement: No-record users can access public group tools
When `get_current_user` returns `None`, `can_access` SHALL still return `True` for tools in the `public` group. A caller with no matching user record and no claim-derived groups is treated as anonymous.

#### Scenario: Unprovisioned user can call public tools
- **WHEN** an authenticated user has no matching MCC user record and no claim-derived groups, and calls a tool in the `public` group
- **THEN** the call succeeds

#### Scenario: Unprovisioned user cannot call non-public tools
- **WHEN** an authenticated user has no matching MCC user record and no claim-derived groups, and calls a tool not in the `public` group
- **THEN** the call returns `"Unauthorized"`

#### Scenario: Claims-only user can call tools in their derived groups
- **WHEN** an authenticated user has no matching MCC user record but claim-derived groups include a group of the called tool
- **THEN** the call succeeds
