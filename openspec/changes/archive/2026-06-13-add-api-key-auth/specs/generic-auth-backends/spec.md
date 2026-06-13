## MODIFIED Requirements

### Requirement: Provider registry maps auth name to FastMCP class
`backend.py` SHALL contain a `_PROXY_PROVIDERS` dict mapping auth name strings to `(module_path, class_name)` tuples for all supported OAuthProxy providers. The registry SHALL include at minimum: `github`, `google`, `azure`, `auth0`, `clerk`, `discord`, `workos`. In addition to the proxy providers, `jwt`, and the dev backends, `get_provider()` SHALL recognize `api_key` as a valid auth backend name and return the API-key `TokenVerifier` for it.

#### Scenario: Known proxy provider name resolves to a class
- **WHEN** `settings.auth` is set to a name present in `_PROXY_PROVIDERS` (e.g., `"google"`)
- **THEN** `get_provider()` dynamically imports the corresponding FastMCP class and returns an instance

#### Scenario: api_key backend returns a TokenVerifier
- **WHEN** `settings.auth` is set to `"api_key"`
- **THEN** `get_provider()` returns the API-key `TokenVerifier` instance

#### Scenario: Unknown auth value raises at startup
- **WHEN** `settings.auth` is set to a value not in `_PROXY_PROVIDERS` and not one of `dev-admin`, `dev-public`, `jwt`, or `api_key`
- **THEN** `get_provider()` raises `ValueError` with the unknown value in the message
