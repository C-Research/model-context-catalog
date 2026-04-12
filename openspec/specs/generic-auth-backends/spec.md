## ADDED Requirements

### Requirement: Provider registry maps auth name to FastMCP class
`backend.py` SHALL contain a `_PROXY_PROVIDERS` dict mapping auth name strings to `(module_path, class_name)` tuples for all supported OAuthProxy providers. The registry SHALL include at minimum: `github`, `google`, `azure`, `auth0`, `clerk`, `discord`, `workos`.

#### Scenario: Known proxy provider name resolves to a class
- **WHEN** `settings.auth` is set to a name present in `_PROXY_PROVIDERS` (e.g., `"google"`)
- **THEN** `get_provider()` dynamically imports the corresponding FastMCP class and returns an instance

#### Scenario: Unknown auth value raises at startup
- **WHEN** `settings.auth` is set to a value not in `_PROXY_PROVIDERS` and not one of `dev-admin`, `dev-public`, or `jwt`
- **THEN** `get_provider()` raises `ValueError` with the unknown value in the message

### Requirement: Proxy providers instantiated via kwargs passthrough
`_build_proxy_provider()` SHALL instantiate the provider class by passing all non-empty values from `settings.oauth.to_dict()` as keyword arguments. Empty strings and `None` values SHALL be excluded.

#### Scenario: oauth settings passed to provider constructor
- **WHEN** `auth: "google"` and `settings.oauth` contains `client_id`, `client_secret`, `base_url`
- **THEN** `GoogleProvider` is instantiated with those three kwargs

#### Scenario: Provider-specific extras forwarded transparently
- **WHEN** `auth: "azure"` and `settings.oauth` contains `client_id`, `client_secret`, `base_url`, `tenant_id`
- **THEN** `AzureProvider` is instantiated with all four kwargs

### Requirement: jwt backend supports any OIDC-compliant provider
When `auth: "jwt"`, `get_provider()` SHALL construct a `RemoteAuthProvider` wrapping a `JWTVerifier` configured from the `jwt:` settings block. The `JWTVerifier` SHALL be initialised with `jwks_uri`, `issuer`, `audience`, and optionally `required_scopes`. The `RemoteAuthProvider` SHALL be initialised with `authorization_servers`, `base_url`, and the verifier.

#### Scenario: Server starts with jwt backend and valid OIDC settings
- **WHEN** `auth: "jwt"` and `settings.jwt` contains `jwks_uri`, `issuer`, `audience`, `authorization_server`, `base_url`
- **THEN** `get_provider()` returns a `RemoteAuthProvider` instance

#### Scenario: jwt backend missing jwks_uri fails at construction
- **WHEN** `auth: "jwt"` and `settings.jwt.jwks_uri` is empty
- **THEN** provider construction raises before the server accepts connections

### Requirement: Dev backends bypass FastMCP provider
When `settings.auth` is `dev-admin` or `dev-public`, `get_provider()` SHALL return `None` and `get_user_context()` SHALL return a `UserModel` directly from the dev helper without calling `get_access_token()`.

#### Scenario: dev-admin returns admin UserModel without a token
- **WHEN** `auth: "dev-admin"` and no HTTP token is present
- **THEN** `get_user_context()` returns a `UserModel` with `"admin"` in groups

#### Scenario: dev-public returns public UserModel without a token
- **WHEN** `auth: "dev-public"` and no HTTP token is present
- **THEN** `get_user_context()` returns a `UserModel` with `"public"` in groups

### Requirement: All OAuth/JWT backends share a single user context call
For any `auth` value that is not `dev-admin` or `dev-public`, `get_user_context()` SHALL call `get_access_token()` from `fastmcp.server.dependencies` and return the resulting token object.

#### Scenario: github backend resolves user context via get_access_token
- **WHEN** `auth: "github"` and a valid token is present in the request
- **THEN** `get_user_context()` returns the access token from FastMCP without provider-specific branching

#### Scenario: jwt backend resolves user context via get_access_token
- **WHEN** `auth: "jwt"` and a valid JWT is present in the request
- **THEN** `get_user_context()` returns the access token from FastMCP without provider-specific branching

### Requirement: github_pat auth backend removed
The `github_pat` auth value and its associated settings block SHALL no longer be supported. `get_user_context()` and `get_provider()` SHALL raise `ValueError` if `auth: "github_pat"` is configured.

#### Scenario: github_pat raises ValueError
- **WHEN** `auth: "github_pat"` is set
- **THEN** calling `get_provider()` or `get_user_context()` raises `ValueError`
