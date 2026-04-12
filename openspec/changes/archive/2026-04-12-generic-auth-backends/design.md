## Context

MCC currently ships two auth backend files: `github_oauth.py` (wires FastMCP's `GitHubProvider`) and `github_pat.py` (calls the GitHub API with a static token from settings — single-user, not multi-user safe). A third change (bearer-auth-middleware) was archived. FastMCP 3.2 ships ~15 provider classes across two families:

- **OAuthProxy** (`GitHubProvider`, `GoogleProvider`, `AzureProvider`, `Auth0Provider`, `ClerkProvider`, `DiscordProvider`, `WorkOSProvider`, …): MCC proxies the OAuth dance, issues its own JWTs. Each needs `client_id`, `client_secret`, `base_url` at minimum; some need provider-specific extras (`tenant_id`, `domain`, `config_url`, etc.).
- **Resource Server** (`JWTVerifier` + `RemoteAuthProvider`): MCC is a pure resource server. Any OIDC-compliant IdP (Okta, Keycloak, Authentik, etc.) issues JWTs; MCC verifies via JWKS.

Every OAuth/JWT provider uses FastMCP's `get_access_token()` for per-request token extraction — the only branching needed is at provider construction time and for dev backends.

## Goals / Non-Goals

**Goals:**
- Support any current or future FastMCP OAuthProxy provider with zero new MCC code (registry entry only)
- Support any OIDC-compliant IdP via a single `jwt` backend
- Delete `github_pat.py` (not multi-user safe)
- Keep dev-admin / dev-public exactly as-is
- Update docs with full backend reference

**Non-Goals:**
- Per-provider claims mapping (identity resolution stays email-first, login fallback — works for all providers that include email)
- Token introspection backend (FastMCP's `IntrospectionTokenVerifier` exists but no operator has asked for it)
- Backwards-compat alias for `github_oauth` → `github` rename

## Decisions

### 1. Single `backend.py` as the only integration point

**Decision:** Delete `github_oauth.py` and `github_pat.py`. All provider logic lives in `backend.py`.

**Rationale:** Each file was ~15 lines of boilerplate. With a registry + factory pattern, `backend.py` handles all providers in ~40 lines total. Adding a new provider = 1 dict entry.

**Alternative considered:** Keep per-provider files, add new ones. Rejected — linear growth, each file nearly identical.

---

### 2. kwargs passthrough for OAuthProxy providers

**Decision:** Instantiate proxy providers via `cls(**{k: v for k, v in settings.oauth.to_dict().items() if v})`. No typed config per provider.

**Rationale:** Provider constructors already validate their own inputs with clear TypeErrors. MCC doesn't need to duplicate that validation. The operator knows which keys their chosen provider needs (documented in FastMCP's provider docs).

**Alternative considered:** Typed Pydantic model per provider in `settings.py`. Rejected — O(n) models, high maintenance, no real benefit since FastMCP validates at construction time anyway.

**Trade-off:** Misconfigured keys surface as `TypeError: unexpected keyword argument` at startup, not a friendly MCC error. Acceptable — startup failures are easy to diagnose.

---

### 3. `jwt` backend for generic OIDC (not named per-provider)

**Decision:** One `jwt` auth value for all OIDC-compliant providers via `JWTVerifier(jwks_uri, issuer, audience)` wrapped in `RemoteAuthProvider`.

**Rationale:** Every OIDC provider exposes the same interface (JWKS endpoint, standard JWT claims). Named wrappers for Okta, Keycloak, etc. would add zero capability.

**Alternative considered:** Named backends for each OIDC provider with pre-filled JWKS URI templates. Rejected — operators know their IdP's JWKS URI; MCC templating adds complexity without value.

---

### 4. `settings.oauth` shared across all proxy providers

**Decision:** One `oauth:` block in settings, used by all proxy providers. Provider-specific extras (e.g., `tenant_id` for Azure) live in the same block.

**Rationale:** Only one proxy provider is active at a time (set by `auth:`). A shared block avoids `azure:`, `google:`, `github:` blocks that are mostly identical.

**Alternative considered:** Per-provider settings namespaces. Rejected — unnecessary when only one is active.

## Risks / Trade-offs

- **Silent misconfiguration on kwargs passthrough** → Mitigation: Python TypeError at startup is clear; document required keys per provider in docs
- **`github_oauth` rename is breaking** → Mitigation: it's a string in a local config file, easy to update; no migration helper needed
- **`jwt` backend fails silently if JWKS URI is unreachable at startup** → Mitigation: `JWTVerifier` raises on first token verification attempt, not at construction; add a note in docs to validate JWKS URI

## Migration Plan

Operators on `github_oauth`:
1. Change `auth: "github_oauth"` → `auth: "github"` in `settings.local.yaml` or env var `MCC_AUTH`
2. Rename settings block: `github_oauth:` → `oauth:`
3. Remove `github_pat:` block if present

No data migration required. No server downtime beyond restart.

**Rollback:** Revert `backend.py` and `settings.yaml` to prior version; rename settings back.

## Open Questions

None — design is fully resolved.
