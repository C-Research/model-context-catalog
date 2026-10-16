## ADDED Requirements

### Requirement: claims settings section
MCC SHALL read claims-based group configuration from a top-level `claims:` settings block (env prefix `MCC_CLAIMS__*`), separate from `oauth:` and `jwt:`. The block SHALL contain `roles_claim` (string, default `""`), `role_group_prefix` (string, default `"MCC:"`), and `require_email_verified` (boolean, default `true`). When `roles_claim` is empty, claims-based group derivation SHALL be disabled and identity resolution SHALL behave exactly as before this change.

#### Scenario: Feature disabled by default
- **WHEN** `claims.roles_claim` is empty
- **THEN** no group is derived from token claims and `get_current_user()` resolves users from the user store only

#### Scenario: Settings overridable by environment
- **WHEN** `MCC_CLAIMS__ROLES_CLAIM` is set in the environment
- **THEN** it overrides `settings.claims.roles_claim`

### Requirement: Empty role_group_prefix rejected at startup
When `claims.roles_claim` is set and `claims.role_group_prefix` is empty, the server SHALL fail at startup with an error naming `role_group_prefix`, regardless of the active auth backend.

#### Scenario: Empty prefix with roles claim configured
- **WHEN** `claims.roles_claim` is `"http://localhost/roles"` and `claims.role_group_prefix` is `""`
- **THEN** startup validation raises before the server accepts connections

#### Scenario: Empty prefix with feature disabled
- **WHEN** `claims.roles_claim` is empty and `claims.role_group_prefix` is `""`
- **THEN** startup validation passes

### Requirement: Groups derived from prefixed roles
`groups_from_claims(claims)` SHALL read the value at the exact key `claims.roles_claim` (no path traversal), keep only list items that are strings starting with `claims.role_group_prefix` (case-sensitive), strip the prefix, and return the remaining non-empty strings as MCC groups, de-duplicated with order preserved. If the claim is absent, not a list, or contains no matching role, it SHALL return an empty list. Non-string list items SHALL be ignored. No group name is treated specially; `MCC:admin` yields the group `admin`.

#### Scenario: Prefixed roles become groups
- **WHEN** the roles claim is `["Acme Portal", "Example MCP", "MCC:osint.geo", "MCC:admin"]` and the prefix is `MCC:`
- **THEN** the derived groups are `["osint.geo", "admin"]`

#### Scenario: Roles without the prefix ignored
- **WHEN** the roles claim is `["Acme Reports", "admin"]`
- **THEN** the derived groups are empty

#### Scenario: Prefix match is case-sensitive
- **WHEN** the roles claim is `["mcc:osint"]` and the prefix is `MCC:`
- **THEN** the derived groups are empty

#### Scenario: Bare prefix ignored
- **WHEN** the roles claim is `["MCC:"]`
- **THEN** the derived groups are empty

#### Scenario: Claim key with dots and slashes
- **WHEN** `roles_claim` is `"http://localhost/roles"` and the claims dict has that exact key
- **THEN** its value is used

#### Scenario: Non-list claim value ignored
- **WHEN** the roles claim value is a string
- **THEN** the derived groups are empty and a warning is logged

### Requirement: Email identity is lowercased and verified
When claims-based derivation is enabled, the identity SHALL be `claims["email"]` lowercased. When `claims.require_email_verified` is true, claims-derived groups SHALL be applied only if `claims["email_verified"]` is `True`; otherwise they SHALL be discarded and a warning logged. When `require_email_verified` is false the `email_verified` claim SHALL NOT be consulted.

#### Scenario: Email lowercased before lookup
- **WHEN** the token has `email` `"Jane.Doe@Example.org"`
- **THEN** the user store is queried with `"jane.doe@example.org"`

#### Scenario: Unverified email discards claim groups
- **WHEN** `require_email_verified` is true and `email_verified` is `False` or absent
- **THEN** no claim groups are applied

#### Scenario: Verification not required
- **WHEN** `require_email_verified` is false and `email_verified` is absent
- **THEN** claim groups are applied

### Requirement: Claim groups are unioned with the user store
When a user-store record matches the caller, `get_current_user()` SHALL return that record with `groups` equal to the record's groups followed by any claim-derived groups not already present; `tools` and `username` SHALL come from the record. When no record matches but claim-derived groups are non-empty, it SHALL return a `UserModel` with `username` and `email` set to the lowercased email, the claim-derived groups, and no tools. If the user-store lookup raises, resolution SHALL continue with claims only.

#### Scenario: Record and claims merged
- **WHEN** the record has groups `["osint"]` and tools `["admin.shell"]` and the claims derive `["osint", "people"]`
- **THEN** the user has groups `["osint", "people"]`, tools `["admin.shell"]`, and the record's username

#### Scenario: Claims-only user
- **WHEN** no record matches and the claims derive `["osint"]`
- **THEN** the user has username equal to the lowercased email, groups `["osint"]`, and no tools

#### Scenario: User store unavailable
- **WHEN** the user-store lookup raises and the claims derive `["osint"]`
- **THEN** the user resolves with groups `["osint"]` rather than as anonymous

### Requirement: Callers with neither a record nor matching roles are anonymous
When no user-store record matches and no claim-derived groups apply, `get_current_user()` SHALL return `None` (resolved as anonymous) and SHALL log at INFO that the caller authenticated but has no record and no matching roles.

#### Scenario: Authenticated user without MCC roles
- **WHEN** a token has a verified email and roles `["Acme Portal"]` and no record matches
- **THEN** `get_current_user()` returns `None` and an INFO line explains why

### Requirement: whoami cache key reflects groups
The `whoami` result cache key SHALL include a hash of the caller's sorted groups in addition to the username, so a change in claim-derived groups does not return a stale cached summary.

#### Scenario: Groups change between calls
- **WHEN** the same username calls `whoami` with different group sets
- **THEN** each group set is cached under a distinct key
