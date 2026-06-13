## Context

MCC authenticates clients through `get_provider()` in `mcc/auth/backend.py`, which maps the single `settings.auth` string to one of: a dev backend (`dev-admin`/`dev-public`, returns `None`), an OAuth proxy provider, or `jwt` (a `RemoteAuthProvider` wrapping a `JWTVerifier`). Identity resolution happens in `mcc/auth/util.py:get_current_user()`, which reads claims (`email` then `login`) off the access token and looks up a `UserModel` in the users index. RBAC lives in `can_access()` and is driven by the `groups`/`tools` fields of that `UserModel`. The `AuthMiddleware` resolves the current user once per request into a contextvar (`mcc/middleware.py`).

A firm OAuth deployment is not ready, but we need authenticated, per-identity, tool-scoped access on the shared prod instance now. API keys are the stopgap.

The clean insight that shapes this design: the existing RBAC and identity-resolution machinery already does everything we need *once we have a username*. So the API-key backend only has to be a thin credential→username bridge; it touches nothing downstream.

## Goals / Non-Goals

**Goals:**
- A new `auth: "api_key"` backend selectable via `settings.auth`, EITHER/OR with existing backends.
- Bearer keys that resolve to a username, reusing the existing `login`-claim resolution path and RBAC unchanged.
- Hashed-only key storage in a dedicated ES index, raw key shown once.
- `mcc user key add/list/revoke` lifecycle.
- Instant revocation.
- A clean precursor to a future composite (multi-backend) auth setup.

**Non-Goals:**
- TLS enforcement in the app (prod infra terminates HTTPS; assumed).
- Composite/multi-backend auth (later, when OAuth firms up).
- Per-key scope (rejected — see Decisions).
- Lookup caching (rejected — conflicts with instant revocation).
- Any change to `can_access()`, `get_current_user()`, `UserModel`, or the users index.

## Decisions

### Identity-only keys; agents are users
A key stores only credential→username. All authorization comes from the users index. To give a key narrow access, model the principal as its own user (e.g. a `ci-bot` user whose `tools` is `["public.request"]`) and bind the key to it.

- **Why over per-key scope:** Per-key scope would require mint-time subset validation, a scoped `UserModel` construction in the resolution path, and a "frozen vs live" decision about whether tool re-grouping or user-grant changes re-widen a key. Modeling the agent as a user reuses existing tooling (`mcc user add`, tool/group grants), keeps `can_access()` untouched, and makes narrowing instant and visible. The only thing lost is "one human identity holding multiple differently-powered keys," which is an OAuth-era power feature, not a get-it-running need.
- **Consequence:** A key grants exactly its bound user's current grants. Narrowing/removing the user instantly narrows the key. There is no path to make a key narrower than its user — that is intentional.

### TokenVerifier as the integration point
Implement `ApiKeyVerifier` as a FastMCP `TokenVerifier` and return it from `get_provider()` under the `api_key` branch, mirroring the `jwt` branch. The interface is async `verify_token(token: str) -> AccessToken | None`. On success it returns `AccessToken(claims={"login": username})`; the existing `get_current_user()` resolves the `UserModel` from there.

- **Why:** It is the smallest possible seam — one branch in `get_provider()`, no middleware change, no change to identity resolution. `AccessToken` already carries a `claims` dict and an `expires_at` epoch field.
- **Alternative considered:** A custom middleware reading the header directly — rejected because it duplicates what FastMCP's auth layer already does (including the 401 on missing/invalid credentials) and would bypass the established `get_access_token()` boundary.

### Hashed storage in a dedicated keys index
New `KeysIndex` in `mcc/db.py` with fields `prefix` (keyword), `hash` (keyword), `username` (keyword), `expires_at` (date), `created_at` (date). Store SHA-256 of the raw key only. Lookup is by `prefix` (indexed), then constant-time compare of `hash`.

- **Key format `mcc_<prefix>_<secret>`:** the literal `mcc_` lets secret scanners (e.g. GitGuardian) flag leaked keys; the prefix segment is the indexed lookup handle; the secret segment is the entropy.
- **Explicit `.create()` required (the footgun):** `UsersIndex` relies on ES auto-mapping on first `put()`, but ES auto-maps strings as `text` + a `.keyword` sub-field. Exact-match lookup on `prefix`/`hash` needs pure `keyword`. So `KeysIndex` must be created with an explicit mapping — mirroring how `ToolIndex` self-creates in `loader.py` — called at first `key add`.
- **One key per identity:** the key document id is the username, so minting overwrites. Prefix → single document; no multi-candidate hash comparison.

### No caching → instant revocation
`verify_token` reads ES on every request. Revoking a key (deleting its record) takes effect on the very next request.

- **Why over caching:** The entire value of API keys over long-lived PATs is revocability. Any cache TTL becomes the revocation-latency window. Given "get it running" priorities and that ES prefix lookup is cheap, we accept the per-request read for correctness and simplicity. Caching can be added later behind a setting if load demands it.

### Default TTL ~90 days
`key add` stamps `expires_at` ~90 days out. `verify_token` rejects expired keys (and `AccessToken.expires_at` can back this at the FastMCP layer too).

- **Why:** Bounds the blast radius of a leaked key even if revocation is forgotten; matches familiar PAT behavior.

## Risks / Trade-offs

- **Raw key leaking into LLM context via the `get_user_context` admin tool** → `mcc/tools/admin.yaml` exposes `get_user_context`, whose docstring warns it may contain sensitive info. Mitigation: the verifier places ONLY `login`/username in `AccessToken` claims, never the raw key; for `api_key` auth `get_user_context` returns at most an access token carrying a username, so there is nothing secret to leak.
- **Raw key leaking into logs** → `LoggingMiddleware` logs tool params, and the `Authorization` header could be logged elsewhere. Mitigation: never log the header or raw key; key material exists in process memory only long enough to hash/compare.
- **Per-request ES read adds latency to every call** → Accepted for instant revocation. Prefix is indexed; lookup is a single exact-match query. Revisit with a TTL setting only if profiling shows it matters.
- **Agents share the users namespace with humans** → `mcc user list` mixes principals and a key could be minted for an admin user, granting broad access. Mitigation: this is the intended model (narrow = bind to a narrow user); `key add` operates on an explicit username so the operator chooses the grant level deliberately. No agent/human distinction is introduced by decision (KISS).
- **A key is a reusable bearer secret over the network** → Mitigated by TLS at the infra layer (assumed, out of app scope), default TTL, and instant revocation.

## Migration Plan

- Additive only. No existing backend, spec, or stored data changes. Default `settings.auth` is unchanged (`dev-admin`).
- Deploy: set `auth: "api_key"` in prod settings, run `mcc user add <principal>` with appropriate tools/groups, then `mcc user key add <principal>` and distribute the key out-of-band.
- Rollback: switch `settings.auth` back to the prior backend. The keys index can be left in place (inert) or dropped.

## Open Questions

- Confirm during implementation that the FastMCP auth layer returns a hard 401 for a missing/invalid `Authorization` header under a bare `TokenVerifier` (so unauthenticated requests never fall through to public-only access). The spec asserts this; verify against the installed FastMCP version and add a test.
