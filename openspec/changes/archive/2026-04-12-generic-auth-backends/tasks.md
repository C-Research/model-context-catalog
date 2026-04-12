## 1. Rewrite backend.py

- [x] 1.1 Add `_PROXY_PROVIDERS` dict mapping names (`github`, `google`, `azure`, `auth0`, `clerk`, `discord`, `workos`) to `(module_path, class_name)` tuples
- [x] 1.2 Implement `_build_proxy_provider(name)` — dynamically imports provider class, passes filtered `settings.oauth.to_dict()` kwargs
- [x] 1.3 Implement `_build_jwt_provider()` — constructs `JWTVerifier(jwks_uri, issuer, audience, required_scopes)` wrapped in `RemoteAuthProvider(token_verifier, authorization_servers, base_url)`
- [x] 1.4 Rewrite `get_provider()` — returns `None` for dev backends, calls `_build_jwt_provider()` for `jwt`, calls `_build_proxy_provider()` for registry names, raises `ValueError` for unknown values
- [x] 1.5 Rewrite `get_user_context()` — dev backends call dev helpers directly; all others call `fast_token = get_access_token` from `fastmcp.server.dependencies`
- [x] 1.6 Remove imports of `github_oauth`, `github_pat`, and `get_provider` alias from `backend.py`

## 2. Delete obsolete files

- [x] 2.1 Delete `mcc/auth/github_oauth.py`
- [x] 2.2 Delete `mcc/auth/github_pat.py`

## 3. Update settings

- [x] 3.1 In `mcc/settings.yaml`: remove `github_oauth:` and `github_pat:` blocks
- [x] 3.2 In `mcc/settings.yaml`: add `oauth:` block with `base_url`, `client_id`, `client_secret` (empty defaults)
- [x] 3.3 In `mcc/settings.yaml`: add `jwt:` block with `jwks_uri`, `issuer`, `audience`, `authorization_server`, `base_url`, `required_scopes` (empty defaults)

## 4. Update docs

- [x] 4.1 Rewrite `docs/auth/backends.md` — remove GitHub OAuth and GitHub PAT sections; add sections for: `dev-admin`, `dev-public`, proxy providers (`github`, `google`, `azure`, `auth0`, `clerk`, `discord`, `workos`) with shared `oauth:` config block and per-provider notes on extra required keys, and `jwt` backend with full OIDC example (Keycloak/Authentik/Okta)
- [x] 4.2 Add migration note to `docs/auth/backends.md` — `github_oauth` → `github`, `github_oauth:` → `oauth:`, `github_pat` removed

## 5. Verify

- [x] 5.1 Run `uv run pytest tests/` — all tests pass
- [x] 5.2 Run `uv run ruff check mcc/auth/` — no lint errors
- [x] 5.3 Run `uv run pyright mcc/auth/` — no type errors
