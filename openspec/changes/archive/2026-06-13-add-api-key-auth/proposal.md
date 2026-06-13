## Why

MCC currently authenticates clients via OAuth proxy providers or JWT/OIDC. Standing up a firm OAuth deployment is not yet done, but we need authenticated, per-identity access to specific tools on the shared prod instance now — for scripts and agents that should each be limited to a narrow set of tools. API keys provide a simple, revocable bearer credential that bridges this gap until OAuth firms up, and the design is a clean precursor to a future composite (multi-backend) setup.

## What Changes

- Add a new `auth: "api_key"` backend, selected via the single `settings.auth` string (EITHER/OR with existing backends — no chaining/composite). It slots into `get_provider()` alongside the `jwt` branch.
- Implement it as a FastMCP `TokenVerifier` (`verify_token(token) -> AccessToken | None`) that resolves a bearer key to a username and returns `AccessToken(claims={"login": username})`, reusing the existing login-based identity resolution. Authorization (tools/groups) continues to come entirely from the existing users index — keys carry no scope of their own.
- Add a new `KeysIndex` in Elasticsearch storing only credential→identity: `prefix`, `hash` (SHA-256, never the raw key), `username`, `expires_at`, `created_at`. One key per identity; minting replaces any existing key for that user.
- Add `mcc user key add/list/revoke` CLI commands. `add` prints the raw key exactly once and replaces any prior key; `list` shows only prefix + created/expiry; `revoke` deletes the record.
- Narrow access is achieved by modeling each principal (script/agent) as its own user with exactly the tools/groups it needs (e.g. a `ci-bot` user limited to `public.request`), then minting a key for it. No agent/human distinction is introduced — everyone is a user.
- Revocation is instant: `verify_token` reads ES on every request (no caching).

## Capabilities

### New Capabilities
- `api-key-auth`: API-key authentication backend — key generation, hashed storage in a dedicated keys index, the `TokenVerifier` that resolves a key to an identity, and the `mcc user key` lifecycle CLI.

### Modified Capabilities
- `generic-auth-backends`: `get_provider()` gains an `api_key` branch; the unknown-auth-value error path now also recognizes `api_key` as a valid backend name.

## Impact

- **Code**: `mcc/auth/backend.py` (new `ApiKeyVerifier`, `get_provider()` branch), `mcc/db.py` (new `KeysIndex` with explicit `.create()`), `mcc/cli/users.py` (new `key` subcommands), `mcc/auth/db.py` or a new module (key CRUD). `can_access()`, `get_current_user()`, `UserModel`, and the users index are UNCHANGED.
- **Config**: new `api_key:` settings block (default TTL ~90 days).
- **Security**: raw keys shown once and never stored; the verifier must place only `login`/username in claims (never the raw key) so the `get_user_context` admin tool and logs cannot leak it. The `Authorization` header / raw key must never be logged.
- **Out of scope**: TLS enforcement (prod infra terminates HTTPS — assumed), composite/multi-backend auth, per-key scoping (rejected in favor of agents-as-users), and lookup caching (rejected for instant revocation).
