## Why

Every person who should reach MCC through an OAuth/JWT backend needs a hand-maintained user record in Elasticsearch, and MCC alone decides which groups they belong to. That does not scale, and it duplicates access management the IdP already does. The IdP's token already carries a role list for the user (e.g. Auth0 roles); MCC should derive tool-group membership from it so access is managed in one place.

## What Changes

- Add a top-level `claims:` settings section (`roles_claim`, `role_group_prefix`, `require_email_verified`). When `roles_claim` is set, `get_current_user()` derives the user's groups from that claim: roles starting with `role_group_prefix` (default `MCC:`) are kept and the prefix is stripped (`MCC:osint.geo` → group `osint.geo`). Admin is an ordinary group.
- Identity is the lowercased `email` claim. With `require_email_verified` (default true) the claim path is skipped unless `email_verified` is true.
- **Union with the user store:** if a record matches the email, its groups and tools are merged with claim groups and its username is used; otherwise the username is the email. If the user store is unavailable, resolution falls back to claims only.
- A caller with no user record and no matching roles resolves to anonymous, with a log line saying why.
- Startup fails if `roles_claim` is set and `role_group_prefix` is empty.
- The `whoami` cache key includes a hash of the user's groups, since claim-derived groups change without any user-store write that would invalidate it.
- Docs: Auth0 setup (tested path, including the Rules→Actions caveat), data-flow update in the auth overview, a note that ES users are now optional, and commented defaults in `settings.yaml`.
- Out of scope: HTTP key routes (`get_user_by_key`) and `mcc tool --as-user` stay user-store-only; GitHub org/team mapping; nested claim paths; the Auth0 tenant's Rules→Actions migration.

## Capabilities

### New Capabilities
- `claims-based-groups`: Deriving group membership and identity from IdP token claims (settings, role→group mapping, email verification, union with the user store, anonymous fallback, startup validation).

### Modified Capabilities
- `oauth2-auth`: `get_current_user` resolution rules change (claims-derived users without a record; anonymous only when there is neither a record nor matching roles), and the "no-record users" requirement is narrowed accordingly.

## Impact

- Code: `mcc/auth/util.py` (resolution), `mcc/settings.py` / `mcc/settings.yaml` (new section, startup validation), `mcc/app.py` (whoami cache key).
- Docs: `docs/auth/backends.md`, `docs/auth/overview.md`, `docs/auth/users-groups.md`.
- No new dependencies. Disabled by default (`roles_claim: ""`), so existing deployments are unchanged until opted in.
- Behavior to document: role removal at the IdP takes effect when the stored token refreshes (10h id_token lifetime on the current Auth0 tenant).
