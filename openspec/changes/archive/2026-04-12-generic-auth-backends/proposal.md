## Why

The current auth system requires a dedicated Python file per provider (github_oauth.py, github_pat.py), meaning every new IdP means new MCC code. FastMCP 3.2 ships ~15 provider classes out of the box — MCC should expose all of them with zero per-provider integration work.

## What Changes

- **BREAKING** `auth: "github_oauth"` renamed to `auth: "github"` in settings
- **BREAKING** `github_oauth:` settings block replaced by `oauth:` (shared across all proxy providers)
- Remove `mcc/auth/github_oauth.py` — logic absorbed into `backend.py`
- Remove `mcc/auth/github_pat.py` — single-user PAT auth eliminated
- Replace `github_pat:` settings block with `jwt:` block for generic OIDC
- `mcc/auth/backend.py` becomes the single integration point: a `_PROXY_PROVIDERS` registry + two factory functions covers every current and future FastMCP provider
- Add `google`, `azure`, `auth0`, `clerk`, `discord`, `workos` as valid `auth:` values (no new code — just registry entries)
- Add `jwt` as a new `auth:` value for any OIDC-compliant provider via `JWTVerifier` + `RemoteAuthProvider`
- Update auth documentation with all supported backends, settings shapes, and per-provider config examples

## Capabilities

### New Capabilities

- `generic-auth-backends`: A single dispatch system in `backend.py` that supports any FastMCP auth provider via a name→class registry (proxy providers) or a `JWTVerifier`+`RemoteAuthProvider` factory (generic OIDC), driven entirely by settings with no per-provider MCC code.

### Modified Capabilities

- `oauth2-auth`: Settings keys and valid `auth:` values are changing; `github_oauth` → `github`, new `oauth:` and `jwt:` blocks replace `github_oauth:` and `github_pat:`.

## Impact

- `mcc/auth/backend.py` — full rewrite
- `mcc/auth/github_oauth.py` — deleted
- `mcc/auth/github_pat.py` — deleted
- `mcc/settings.yaml` — settings keys changed
- `docs/` — auth page added/updated
- Tests referencing `auth: "github_oauth"` or `github_pat` need updating
- Operators using `github_oauth` backend must update their `settings.local.yaml` or env vars
