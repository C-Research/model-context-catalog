## Context

`get_current_user()` (`mcc/auth/util.py`) turns an `AccessToken` into a `UserModel` by looking up the token's `email` (then `login`) claim in the Elasticsearch users index. Groups and tools come only from that record, so every OAuth/JWT user must be provisioned by hand; an unknown user is anonymous.

FastMCP already hands us the IdP's claims: for proxy providers `load_access_token` re-verifies the stored upstream token on each request and returns its decoded claims (the id_token when `oauth.verify_id_token` is true; the access token otherwise), and the `jwt` backend returns the decoded access token. On the current Auth0 tenant the id_token carries `email`, `email_verified`, and a list of role names under a namespaced key (`http://localhost/roles`, emitted by a legacy Auth0 Rule). Roles there are tenant-wide and shared across several applications (`Acme Portal`, `Acme Reports`, `Example MCP`, ...).

Constraints:
- Everything under `oauth:` is passed as kwargs to the FastMCP provider constructor (`_build_proxy_provider`), so new settings cannot live there.
- `UserModel` and `can_access` stay as they are; this change only alters how the `UserModel` is produced.
- Only Auth0 is run and tested; the code is OSS and should work for any backend whose claims contain a list of role names.

## Goals / Non-Goals

**Goals:**
- Manage MCC tool-group membership in the IdP, with no per-user ES record required.
- Backend-agnostic: reads `token.claims`, configured by settings only.
- Existing deployments and ES-provisioned users unaffected until opted in.
- Fail closed: a misconfigured or missing claim yields no groups, never extra ones.

**Non-Goals:**
- GitHub org/team (or Google Workspace group) membership; those claims carry no roles.
- Nested/dotted claim paths (e.g. Keycloak `realm_access.roles`).
- Changing the HTTP key routes (`get_user_by_key`) or `mcc tool --as-user`; they remain user-store-only.
- Migrating the Auth0 tenant from Rules to Actions.
- Instant revocation; claim-derived groups update when the stored token refreshes.

## Decisions

**1. New top-level `claims:` section, not keys under `oauth:`.**
`oauth.*` is splatted into the provider constructor; an extra key would raise `TypeError` at startup. A separate section also keeps the feature independent of which backend is active (it works for `jwt` too). Alternative: pop the keys inside `_build_proxy_provider` like `client_storage_backend` — rejected because it couples the feature to the proxy-provider path.

Settings: `roles_claim` (default `""`, feature off), `role_group_prefix` (default `MCC:`), `require_email_verified` (default `true`). `roles_claim` has no default because the namespace is tenant-specific.

**2. Prefix filter, not an IdP-role→group map.**
Roles are tenant-wide, so passing role names through would turn another team's `admin` role into MCC admin. A case-sensitive prefix keeps only roles intended for MCC, and stripping it is itself the mapping (`MCC:osint.geo` → `osint.geo`), so no per-role config is needed. Role names without the prefix, and a bare prefix with nothing after it, are ignored. Startup fails if `roles_claim` is set and the prefix is empty, since an empty prefix would adopt every role. Alternative: an explicit map in settings — rejected as more config for no added safety; can be added later if a need appears. Admin is not special-cased: `MCC:admin` yields group `admin`.

**3. Exact-key claim lookup.**
Auth0 custom claims are URL-shaped keys full of dots and slashes, so the claim is read with a plain `claims.get(roles_claim)`; no path traversal. The value must be a list of strings; anything else is ignored with a warning (fail closed).

**4. Identity is the lowercased `email` claim, gated on `email_verified`.**
Email is the primary identifier and is lowercased before lookup and before use as a username, so ES term matches and rate-limit/session keys don't split on case. With `require_email_verified` true (default) the claim path is skipped unless `claims["email_verified"] is True`. This is redundant with the current Auth0 Rule but becomes the only gate if that Rule is removed. The flag exists so backends that drop the claim (e.g. Cognito's default verifier) can still opt in; Auth0 never touches it. The existing `login`-claim fallback to the user store (GitHub) is unchanged. The users index `email` field gets the built-in `lowercase` normalizer (`USERS_MAPPING` in `mcc/db/base.py`), making term queries (user lookup, duplicate-email check) case-insensitive, so no second lookup with the raw casing is needed. A mapping can't be changed on an existing index, so this applies only to newly created indices; existing deployments keep working because their emails are already lowercase and the claim email is lowercased before lookup, but they need a recreate/reindex before mixed-case records match. Not verified on OpenSearch (only Elasticsearch 8.x).

**5. Union with the user store.**
Resolution order in `get_current_user()`:
1. Look up the user store by email (then `login`), as today. If the store raises, log and continue with no record (claims-only) instead of returning anonymous.
2. If `roles_claim` is configured and the email gate passes, compute claim groups from the prefix filter.
3. If a record exists: return it with `groups = record.groups ∪ claim_groups` (order preserved, de-duplicated); `tools` and `username` come from the record.
4. If there is no record but claim groups are non-empty: return `UserModel(username=email, email=email, groups=claim_groups)`.
5. Otherwise return `None` (→ anonymous), logging that the caller authenticated but has no record and no matching roles.

Union rather than replace so existing users keep per-user `tools` grants and migration is incremental; the trade-off is that a lingering ES group survives removal of the IdP role. Falling back to claims-only on a store failure can only reduce permissions, so it is safe.

**6. Group-derived `whoami` cache key.**
`whoami:{username}` is invalidated by user-store writes, which claim-derived groups never trigger. The key becomes `whoami:{username}:{hash(sorted groups)}`. The `execute` cache key already hashes the identity fields, so it needs no change. Because the key is no longer exact per user, `_invalidate_whoami` in `mcc/auth/db.py` switches from `cache.delete` to `cache.delete_match(f"whoami:{username}:*")`, and the existing whoami cache tests prime the new key format.

**7. Placement.**
A pure helper `groups_from_claims(claims)` and a `validate_claims_settings()` live in `mcc/auth/util.py` and are exported from `mcc.auth`; `validate_claims_settings()` is called at startup in `mcc/app.py` next to `validate_rate_limit_settings()`, independent of the active backend. No ES/db changes.

## Risks / Trade-offs

- **Revocation lag** → claim groups change only when the stored upstream token refreshes (10h id_token lifetime on the current tenant). Document it; operators can shorten the lifetime in Auth0. Not confirmed: whether Auth0 re-runs the Rule/Action on refresh-token exchange.
- **Auth0 Rules are deprecated** → the `http://localhost/roles` claim and the app-access/email-verified gate both live in legacy Rules slated for removal. If the claim disappears, claim users fall to anonymous (fail closed). Document that a post-login Action emitting its own namespaced claim is the durable path; settings-only change on our side.
- **Anyone who can assign Auth0 roles can grant MCC admin** (`MCC:admin`) → accepted; documented.
- **Authenticated-but-anonymous confusion** → `whoami` says "Not authenticated" for a verified IdP user with no `MCC:` roles; mitigated by an INFO log line stating the reason.
- **Per-request ES read remains** (union) → same cost as today.
- **Claims logged at INFO** (`util.py`) now include roles → left as is per decision.

## Migration Plan

Fully backward compatible; steps can happen in any order:
1. (Optional, durable) Add an Auth0 post-login Action emitting the roles under a real namespace.
2. Deploy MCC with the `claims:` section set (`roles_claim`, optionally `role_group_prefix`).
3. Create `MCC:<group>` roles in the IdP and assign users; existing sessions pick them up when their token refreshes.
4. Delete ES user records that are now redundant.

Rollback: unset `claims.roles_claim`; resolution reverts to the user-store-only behavior.
