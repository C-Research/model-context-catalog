## 1. Settings

- [x] 1.1 Add the `claims:` block (`roles_claim: ""`, `role_group_prefix: "MCC:"`, `require_email_verified: true`) to `mcc/settings.yaml` with explanatory comments
- [x] 1.2 Add `validate_claims_settings()` in `mcc/auth/util.py` that raises `ValueError` naming `role_group_prefix` when `roles_claim` is set and the prefix is empty; export it from `mcc.auth`
- [x] 1.3 Call `validate_claims_settings()` at startup in `mcc/app.py`, independent of the active auth backend

## 2. Claim → group derivation

- [x] 2.1 Add `groups_from_claims(claims)` in `mcc/auth/util.py`: exact-key lookup, list-of-strings only, case-sensitive prefix filter, strip prefix, drop empty/non-string items, de-duplicate preserving order; warn on a non-list value
- [x] 2.2 Export `groups_from_claims` from `mcc.auth`

## 3. Identity resolution

- [x] 3.1 In `get_current_user()`, lowercase the `email` claim before the user-store lookup
- [x] 3.2 Gate claim-derived groups on `email_verified is True` when `require_email_verified` is true; warn and discard otherwise
- [x] 3.3 Union claim groups into a matched record (record groups first, de-duplicated; tools and username from the record)
- [x] 3.4 Build a claims-only `UserModel` (username = email, groups = derived, no tools) when no record matches but groups were derived
- [x] 3.5 On user-store failure, continue with claims only instead of returning `None`
- [x] 3.6 Return `None` with an INFO log (authenticated, no record, no matching roles) when neither a record nor groups apply
- [x] 3.7 Leave the `login`-claim fallback, API-key path, `get_user_by_key`, and `mcc tool --as-user` unchanged

## 4. whoami cache key

- [x] 4.1 Change the `whoami` cache key in `mcc/app.py` to include a hash of the caller's sorted groups

## 5. Tests

- [x] 5.1 `groups_from_claims`: prefixed roles, unprefixed ignored, case sensitivity, bare prefix, dotted/URL claim key, non-list value, non-string items, de-duplication
- [x] 5.2 `validate_claims_settings`: empty prefix with and without `roles_claim`
- [x] 5.3 `get_current_user`: lowercased email lookup, unverified email, `require_email_verified` false, union with a record, claims-only user, user-store failure, anonymous when nothing applies, feature disabled by default
- [x] 5.4 `can_access` end-to-end for a claims-only user (derived group grants access; no groups → public only)
- [x] 5.5 `whoami` cache key differs for different group sets

## 6. Docs

- [x] 6.1 `docs/auth/backends.md`: Auth0 section covering `MCC:` roles, the `claims:` settings, tested-path status, the Rules→Actions caveat, and the revocation lag
- [x] 6.2 `docs/auth/backends.md`: note which other backends should work (claims carry a role list) versus those that cannot (GitHub, Google, Discord, WorkOS, Clerk); mark them untested
- [x] 6.3 `docs/auth/overview.md`: update the data-flow diagram and describe claim-derived groups and the anonymous fallback
- [x] 6.4 `docs/auth/users-groups.md`: state that ES users are optional for claims-derived access and still required for API keys, per-user tool grants, HTTP key routes, and `--as-user`

## 7. Verification

- [x] 7.1 Run `uv run pytest -x tests/`, `uv run ruff check .`, `uv run pyright`, and `uv run bandit -c pyproject.toml -r .`; all four must pass
