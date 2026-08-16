## MODIFIED Requirements

### Requirement: Keys index stores hashed credential to identity mapping
The system SHALL store API keys in a dedicated index (`KeysIndex`) separate from the users index, backed by Elasticsearch or OpenSearch depending on `settings.SEARCH_BACKEND`. Each document SHALL contain `prefix` (keyword), `hash` (keyword, SHA-256 of the raw key), `username` (keyword), `expires_at` (date), and `created_at` (date). The index SHALL NOT store the raw key. The keys index SHALL carry identity only; all authorization (tools/groups) SHALL continue to come from the users index. `KeysIndex`'s document schema and CRUD behavior SHALL be identical between backends since it performs no backend-specific search/vector logic.

#### Scenario: Key record contains hash, not raw key
- **WHEN** a key is minted for user `ci-bot`
- **THEN** the stored document contains `prefix`, `hash`, `username="ci-bot"`, `expires_at`, and `created_at`, and does NOT contain the raw key

#### Scenario: Keys index mapping uses keyword fields for exact lookup
- **WHEN** the keys index is created
- **THEN** `prefix` and `hash` are mapped as `keyword` (not `text`), on either backend, so exact-match lookups resolve correctly

#### Scenario: KeysIndex CRUD parity across backends
- **WHEN** a key document is put and then retrieved via `KeysIndex`, first with `search_backend: elasticsearch` and then with `search_backend: opensearch`
- **THEN** both backends return the same stored document for the same operations

### Requirement: Keys index is created explicitly
Unlike the users index (which relies on auto-mapping on first write), the keys index SHALL be created with an explicit mapping via a `.create()` call before or upon first key write, on either backend. This ensures `prefix` and `hash` are typed as `keyword` rather than auto-mapped as `text`.

#### Scenario: First key add creates the index with explicit mapping
- **WHEN** `mcc user key add` is run and the keys index does not yet exist
- **THEN** the index is created with the explicit `keyword` mapping before the key document is written, regardless of which backend is configured
