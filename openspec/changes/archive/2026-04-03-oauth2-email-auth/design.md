## Context

MCC currently authenticates clients using manually-issued bearer tokens stored as SHA-256 hashes in TinyDB. Tokens are distributed out-of-band via the CLI and tied to a `username` field. This creates operational overhead (token rotation, distribution) and a bespoke identity model.

FastMCP 3.2 ships `GitHubProvider`, a complete OAuth2 proxy that handles the full GitHub OAuth flow, token validation via GitHub's API, and user info extraction. Replacing the custom middleware with this provider eliminates token management from MCC entirely.

## Goals / Non-Goals

**Goals:**
- Replace `BearerAuthMiddleware` with FastMCP's `GitHubProvider` as `mcp.auth`
- Store both GitHub `login` (username) and `email` (if present) per user record
- Resolve identity preferring email when present, falling back to username
- Keep the permission model (`groups`, `tools`, `can_access`) entirely unchanged
- Provide `get_current_user(ctx)` helper to resolve an `AccessToken` → user dict in one call
- Allow unauthenticated access to `public` group tools even when no user record is found

**Non-Goals:**
- Supporting OAuth providers other than GitHub
- Auto-provisioning users on first login — admin must pre-create user records
- Migrating existing TinyDB records automatically
- Fetching private GitHub emails via `/user/emails`

## Decisions

### D1: Store both username and email; prefer email for identity resolution
GitHub's `login` claim is always present and stable (GitHub handle). `email` is human-readable but optional (null if private). Both are stored in the user record. `get_current_user` tries email first — if the claim is non-null and matches a record, that record is used. If not, it falls back to `login`. This lets admins provision users by GitHub handle (always works) and optionally associate an email for users who expose one.

*Alternative considered*: Email-only. Rejected — users without a public email would never resolve to a user record, blocking all non-public access regardless of whether the admin knows their GitHub handle.

### D2: `GitHubProvider` directly, not `MultiAuth` + custom verifier
`GitHubProvider` is a complete `OAuthProxy` — it owns the OAuth authorization endpoints, token exchange, and token verification via GitHub's `/user` API. No custom `TokenVerifier` subclass or JWT library is needed. Wired as `mcp.auth = GitHubProvider(...)`.

*Alternative considered*: `MultiAuth` with a custom `JWKSTokenVerifier`. Rejected — GitHub tokens are opaque (not JWTs).

### D3: `get_current_user(ctx)` helper instead of middleware state
`get_access_token()` makes the validated `AccessToken` available in any request context. The helper calls `get_access_token()`, tries email → username resolution in order, and returns the matching user dict. Keeps lookup co-located with where permissions are checked.

*Alternative considered*: Post-auth middleware to set ctx state. Rejected — the helper is simpler.

### D4: Identity resolution order — email first, username fallback
```
get_current_user():
  token = get_access_token()           # None → return None
  email = token.claims.get("email")    # try email first
  if email:
    user = get_user_by_email(email)
    if user: return user
  login = token.claims.get("login")    # fall back to GitHub handle
  if login:
    return get_user_by_username(login) # None if not provisioned
  return None
```
Users without a public email still resolve if provisioned by username. Public tools remain accessible when `get_current_user` returns `None`.

### D5: Configuration via environment variables
`GitHubProvider` requires `client_id`, `client_secret`, and `base_url`. Read from `MCC_GITHUB_CLIENT_ID`, `MCC_GITHUB_CLIENT_SECRET`, and `MCC_BASE_URL` at startup.

## Risks / Trade-offs

- **Email mutability** → If a user changes their GitHub email, email-based lookup fails but username fallback still resolves them. Lower risk than email-only.
- **Username change** → GitHub allows handle changes; if a user renames their account the username lookup breaks. Mitigation: admin updates the record; rare in practice.
- **GitHub API dependency** → Token verification requires a live call to `api.github.com`. Mitigation: configure `MCC_GITHUB_CACHE_TTL`.
- **Existing bearer tokens break** → Breaking change on deploy; document and coordinate.

## Migration Plan

1. Register a GitHub OAuth App; note client ID and secret
2. Deploy new code with `MCC_GITHUB_CLIENT_ID`, `MCC_GITHUB_CLIENT_SECRET`, `MCC_BASE_URL` set
3. Admin recreates user records via `mcc add-user --username <github-handle> [--email <email>]` and re-grants permissions
4. Clients authenticate via the GitHub OAuth flow and connect with the resulting token
5. Delete old `users.db` or leave orphaned `token_hash` fields (TinyDB ignores them)

Rollback: revert code deploy; old `users.db` records remain intact.

## Open Questions

- Should `MCC_GITHUB_CACHE_TTL` default to a non-zero value (e.g. 300s) to reduce GitHub API load?
