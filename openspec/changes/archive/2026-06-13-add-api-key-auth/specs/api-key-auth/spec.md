## ADDED Requirements

### Requirement: API key format and generation
The system SHALL generate API keys in the format `mcc_<prefix>_<secret>`, where `prefix` is a short random identifier used for index lookup and `secret` is cryptographically random. The `mcc_` literal prefix makes leaked keys detectable by secret scanners. The full raw key SHALL be returned to the caller exactly once at creation and SHALL NOT be recoverable thereafter.

#### Scenario: Generated key has the mcc_ prefix
- **WHEN** a key is minted for a user
- **THEN** the returned raw key string starts with `mcc_` and contains a prefix segment and a secret segment

#### Scenario: Raw key is shown only at creation
- **WHEN** a key is minted
- **THEN** the raw key is returned to the caller, and no stored record contains the raw key (only a hash and the prefix)

### Requirement: Keys index stores hashed credential to identity mapping
The system SHALL store API keys in a dedicated Elasticsearch index (`KeysIndex`) separate from the users index. Each document SHALL contain `prefix` (keyword), `hash` (keyword, SHA-256 of the raw key), `username` (keyword), `expires_at` (date), and `created_at` (date). The index SHALL NOT store the raw key. The keys index SHALL carry identity only; all authorization (tools/groups) SHALL continue to come from the users index.

#### Scenario: Key record contains hash, not raw key
- **WHEN** a key is minted for user `ci-bot`
- **THEN** the stored document contains `prefix`, `hash`, `username="ci-bot"`, `expires_at`, and `created_at`, and does NOT contain the raw key

#### Scenario: Keys index mapping uses keyword fields for exact lookup
- **WHEN** the keys index is created
- **THEN** `prefix` and `hash` are mapped as `keyword` (not `text`) so exact-match lookups resolve correctly

### Requirement: Keys index is created explicitly
Unlike the users index (which relies on Elasticsearch auto-mapping on first write), the keys index SHALL be created with an explicit mapping via a `.create()` call before or upon first key write. This ensures `prefix` and `hash` are typed as `keyword` rather than auto-mapped as `text`.

#### Scenario: First key add creates the index with explicit mapping
- **WHEN** `mcc user key add` is run and the keys index does not yet exist
- **THEN** the index is created with the explicit `keyword` mapping before the key document is written

### Requirement: One key per identity
The system SHALL maintain at most one active key per user. Minting a key for a user who already has one SHALL replace the existing key. A key prefix SHALL map to a single key document.

#### Scenario: Minting replaces an existing key
- **WHEN** `mcc user key add ci-bot` is run and `ci-bot` already has a key
- **THEN** the prior key is replaced, the prior key no longer validates, and a new raw key is returned

### Requirement: TokenVerifier resolves a key to an identity
When `auth: "api_key"`, `get_provider()` SHALL return a FastMCP `TokenVerifier` whose async `verify_token(token)` method extracts the prefix, looks up the key document in the keys index, performs a constant-time comparison of the SHA-256 hash, checks expiry, and on success returns an `AccessToken` with `claims={"login": <username>}`. On any failure (unknown prefix, hash mismatch, expired, or missing record) it SHALL return `None`. The verifier SHALL NOT place the raw key in `AccessToken` claims or scopes.

#### Scenario: Valid key resolves to its user identity
- **WHEN** a request presents a valid, unexpired key for `ci-bot`
- **THEN** `verify_token` returns an `AccessToken` whose `claims["login"]` is `ci-bot`

#### Scenario: Unknown or malformed key is rejected
- **WHEN** a request presents a key whose prefix is not found or whose hash does not match the stored hash
- **THEN** `verify_token` returns `None`

#### Scenario: Expired key is rejected
- **WHEN** a request presents a key whose `expires_at` is in the past
- **THEN** `verify_token` returns `None`

#### Scenario: Raw key never appears in claims
- **WHEN** `verify_token` succeeds
- **THEN** the returned `AccessToken` claims and scopes contain the username/login but never the raw key string

### Requirement: Authorization derives from the users index unchanged
The API-key backend SHALL NOT alter `can_access()`, `get_current_user()`, `UserModel`, or the users index. After `verify_token` returns an identity, the existing login-based resolution SHALL resolve the `UserModel` from the users index and the existing RBAC SHALL apply. A key therefore grants exactly the tools/groups of its bound user; narrowing access is achieved by binding the key to a user with narrow grants.

#### Scenario: Key grants exactly its user's tools
- **WHEN** a key is bound to user `ci-bot` whose `tools` is `["public.request"]`
- **THEN** requests using that key can execute `public.request` and are denied any tool the `ci-bot` user cannot access

#### Scenario: Narrowing a user instantly narrows its key
- **WHEN** the `ci-bot` user's grants are reduced
- **THEN** subsequent requests using the bound key reflect the reduced grants without re-minting the key

### Requirement: Revocation is instant
The verifier SHALL read the keys index on every request without caching, so that deleting a key record takes effect immediately on the next request.

#### Scenario: Revoked key stops working immediately
- **WHEN** a key is revoked (its record deleted) and a request presents that key
- **THEN** the next request is rejected with no caching delay

### Requirement: Missing or invalid credential is rejected at the transport layer
When `auth: "api_key"` is configured, a request with no `Authorization` header or an invalid bearer key SHALL be rejected (HTTP 401) by the FastMCP auth layer and SHALL NOT fall through to unauthenticated/public-only access.

#### Scenario: Request without Authorization header is rejected
- **WHEN** `auth: "api_key"` and a request arrives with no `Authorization` header
- **THEN** the request is rejected with 401 and no tool is executed

### Requirement: mcc user key CLI commands
The CLI SHALL provide `mcc user key add <username>`, `mcc user key list`, and `mcc user key revoke <username>`. `add` SHALL mint and print the raw key exactly once (replacing any existing key) and apply a default TTL of approximately 90 days. `list` SHALL display only the prefix and created/expiry timestamps and SHALL NOT display anything key-derived such as the hash. `revoke` SHALL delete the user's key record.

#### Scenario: key add prints the raw key once
- **WHEN** `mcc user key add ci-bot` is run
- **THEN** the raw key is printed once with guidance to copy it, and a record with default ~90 day expiry is stored

#### Scenario: key list does not reveal secrets
- **WHEN** `mcc user key list` is run
- **THEN** output shows prefix, created, and expiry per key, and does NOT show the hash or any raw key

#### Scenario: key revoke removes the key
- **WHEN** `mcc user key revoke ci-bot` is run
- **THEN** the key record for `ci-bot` is deleted and that key no longer validates
