## 1. Settings

- [x] 1.1 Add an `api_key:` block to `mcc/settings.yaml` with `default_ttl_days: 90`.

## 2. Keys storage

- [x] 2.1 Add `KeysIndex(ESIndex)` to `mcc/db.py` with an explicit mapping: `prefix` (keyword), `hash` (keyword), `username` (keyword), `expires_at` (date), `created_at` (date). Bind `index` to a new `ELASTICSEARCH__KEY_INDEX` setting.
- [x] 2.2 Add a key module (e.g. `mcc/auth/keys.py`) with key generation (`mcc_<prefix>_<secret>` using `secrets`), SHA-256 hashing, and constant-time compare (`hmac.compare_digest`).
- [x] 2.3 Implement key CRUD: `create_key(username, ttl_days)` (mints, computes `expires_at`/`created_at`, calls `KeysIndex.create()` then `put` keyed by username, returns the raw key once), `get_key_by_prefix(prefix)`, `list_keys()`, `revoke_key(username)`.

## 3. TokenVerifier backend

- [x] 3.1 Implement `ApiKeyVerifier(TokenVerifier)` in `mcc/auth/backend.py` with async `verify_token(token)`: parse prefix → `get_key_by_prefix` → constant-time hash compare → expiry check → return `AccessToken(claims={"login": username})`, else `None`. Never put the raw key in claims/scopes.
- [x] 3.2 Add the `auth == "api_key"` branch to `get_provider()` returning `ApiKeyVerifier`, and add `api_key` to the recognized backends so unknown-value `ValueError` excludes it.

## 4. CLI

- [x] 4.1 Add a `key` subgroup under `mcc user` in `mcc/cli/users.py`.
- [x] 4.2 `mcc user key add <username>`: verify the user exists, mint+replace the key, print the raw key exactly once with copy guidance and expiry.
- [x] 4.3 `mcc user key list`: print prefix + created + expiry only (never hash or raw key).
- [x] 4.4 `mcc user key revoke <username>`: delete the key record; error if none exists.

## 5. Hardening

- [x] 5.1 Confirm the `Authorization` header / raw key is never logged (audit `LoggingMiddleware` and the verifier); ensure key material is not retained beyond hashing/compare.
- [x] 5.2 Verify (and add a test) that under `auth: "api_key"` a missing/invalid `Authorization` header yields a hard 401 and does not fall through to public-only access.

## 6. Tests

- [x] 6.1 Test `ApiKeyVerifier.verify_token`: valid key resolves to `login`; unknown prefix, hash mismatch, and expired key each return `None`; raw key never in claims.
- [x] 6.2 Test key CRUD + index: explicit `keyword` mapping created on first add; minting replaces an existing key; revoke deletes; instant revocation (no cache).
- [x] 6.3 Test `get_provider()` returns `ApiKeyVerifier` for `api_key` and still raises `ValueError` for an unknown auth value.
- [x] 6.4 Test the `mcc user key` CLI: `add` prints raw key once, `list` reveals no secrets, `revoke` removes the key.
- [x] 6.5 Integration test: a key bound to a narrow user (e.g. tools `["public.request"]`) can execute that tool and is denied others; narrowing the user narrows the key without re-minting.

## 7. Verification

- [x] 7.1 Run `uv run pytest tests/`, `uv run ruff check`, and `uv run pyright` per AGENTS.md; all pass.
- [x] 7.2 Update docs under `docs/` (and register any new page in `mkdocs.yml`) describing the `api_key` backend, the agents-as-users model, and the `mcc user key` commands.
