---
icon: lucide/server
---

# Auth Backends

Configure the active auth backend with the `auth` setting (or `MCC_AUTH` env var).

```yaml
# settings.local.yaml
default:
  auth: "dev-admin"   # default
```

---

## Dev Backends

### dev-admin

No authentication — automatically selects the first admin user in the database. Falls back to a synthetic user with `groups: [admin]` if none exists.

!!! danger "Never use in production"
    Any request gets full admin access. For local development only.

```yaml
default:
  auth: "dev-admin"
```

### dev-public

No authentication — automatically selects the first public user in the database. Falls back to a synthetic user with `groups: [public]` if none exists.

```yaml
default:
  auth: "dev-public"
```

Useful for testing the public tool surface without granting admin access. Safe to use in production for fully public deployments.

---

## API Key (`api_key`)

A simple, revocable bearer-token backend for scripts and agents — a stopgap
until a full OAuth deployment is in place. Each caller presents an
`Authorization: Bearer mcc_<prefix>_<secret>` header; MCC resolves the key to a
username and applies that user's existing tools/groups. Keys carry **no scope of
their own** — all authorization comes from the users index, unchanged.

```yaml
default:
  auth: "api_key"
  api_key:
    default_ttl_days: 90   # keys expire after ~90 days
```

### Agents are users

There is no separate agent/key permission model. To give a key narrow access,
model the principal as its own user with exactly the tools/groups it needs, then
mint a key for it:

```bash
mcc user add ci-bot --tool public.request   # a narrow principal
mcc user key add ci-bot                      # mint its key (shown once)
```

The key grants exactly `ci-bot`'s current grants. **Narrowing the user instantly
narrows the key** — revoke a tool with `mcc user revoke` and the next request
reflects it, no re-minting required. There is no way to make a key *narrower*
than its bound user; that is intentional.

### Security properties

- **Hashed storage.** Only a SHA-256 hash, the lookup prefix, and an expiry are
  stored in a dedicated keys index — never the raw key. The raw key is shown
  exactly once at creation and cannot be recovered.
- **Instant revocation.** The verifier reads Elasticsearch on every request with
  no caching, so `mcc user key revoke` takes effect immediately.
- **Default TTL.** Keys expire ~90 days out (`api_key.default_ttl_days`),
  bounding the blast radius of a leaked key. Override per key with
  `mcc user key add --expires <days|never>`.
- **No leakage into LLM context or logs.** Only the username appears in the
  resolved identity; the raw key and `Authorization` header are never logged.
- **Hard 401.** A missing or invalid key is rejected at the transport layer and
  never falls through to public-only access.

!!! note "TLS is assumed"
    A key is a reusable bearer secret. MCC assumes HTTPS is terminated by your
    infrastructure; the app does not enforce TLS itself.

See [Users & Groups](users-groups.md#api-keys) for the full `mcc user key`
command reference.

---

## OAuth Proxy Backends

!!! warning "Under construction"
    This is a work in progress as OAuth2 providers are still untested 

These backends proxy the OAuth 2.0 authorization flow to an external identity provider. MCC validates tokens and issues its own short-lived JWTs to MCP clients.

All proxy backends read credentials from the shared `oauth:` settings block. Remember you can set this via env vars ie `MCC_OAUTH__CLIENT_ID=xxx`

```yaml
default:
  oauth:
    base_url: "https://your-mcc-server.example.com"
    client_id: "your-client-id"
    client_secret: "your-client-secret"
```

Or via environment variables: `MCC_OAUTH__BASE_URL`, `MCC_OAUTH__CLIENT_ID`, `MCC_OAUTH__CLIENT_SECRET`.

Users must exist in the MCC user store before they connect. Identity is resolved from the token's `email` claim first, then `login` (GitHub handle):

```bash
mcc user add alice --email alice@example.com
```

### github

Authenticates via GitHub OAuth. Requires a [GitHub OAuth App](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/creating-an-oauth-app).

```yaml
default:
  auth: "github"
  oauth:
    base_url: "https://your-mcc-server.example.com"
    client_id: "Ov23li..."
    client_secret: "abc123..."
```

### google

Authenticates via Google OAuth. Requires a [Google OAuth 2.0 client](https://console.cloud.google.com/apis/credentials).

```yaml
default:
  auth: "google"
  oauth:
    base_url: "https://your-mcc-server.example.com"
    client_id: "123456789.apps.googleusercontent.com"
    client_secret: "GOCSPX-..."
```

### azure

Authenticates via Microsoft Entra ID (Azure AD). Requires `tenant_id` in addition to the standard fields.

```yaml
default:
  auth: "azure"
  oauth:
    base_url: "https://your-mcc-server.example.com"
    client_id: "your-app-client-id"
    client_secret: "your-app-client-secret"
    tenant_id: "your-tenant-id"
```

### auth0

Authenticates via Auth0. Requires `config_url` and `audience` (the identifier
of an [Auth0 API](https://auth0.com/docs/get-started/apis) registered in your
tenant).

```yaml
default:
  auth: "auth0"
  oauth:
    base_url: "https://your-mcc-server.example.com"
    client_id: "your-auth0-client-id"
    client_secret: "your-auth0-client-secret"
    config_url: "https://your-tenant.auth0.com/.well-known/openid-configuration"
    audience: "https://your-api-identifier"
```

Identity is resolved from the `email` claim (see [Generic OIDC
Backend](#generic-oidc-backend-jwt)). By default MCC verifies Auth0's
**access token**, which does not carry `email` unless you add a tenant-side
Action to inject it. Set `verify_id_token: true` to verify the **id_token**
instead, whose standard OIDC claims include `email` natively with no
tenant-side Action required:

```yaml
    oauth:
      ...
      verify_id_token: true
```

### clerk

Authenticates via Clerk. Requires `domain`.

```yaml
default:
  auth: "clerk"
  oauth:
    base_url: "https://your-mcc-server.example.com"
    client_id: "your-clerk-client-id"
    client_secret: "your-clerk-client-secret"
    domain: "your-app.clerk.accounts.dev"
```

### discord

Authenticates via Discord OAuth.

```yaml
default:
  auth: "discord"
  oauth:
    base_url: "https://your-mcc-server.example.com"
    client_id: "your-discord-client-id"
    client_secret: "your-discord-client-secret"
```

### workos

Authenticates via WorkOS AuthKit. Requires `authkit_domain`.

```yaml
default:
  auth: "workos"
  oauth:
    base_url: "https://your-mcc-server.example.com"
    client_id: "your-workos-client-id"
    client_secret: "your-workos-client-secret"
    authkit_domain: "your-app.authkit.app"
```

### aws

Authenticates via AWS Cognito. Requires `user_pool_id` and `aws_region` in addition to the standard fields.

```yaml
default:
  auth: "aws"
  oauth:
    base_url: "https://your-mcc-server.example.com"
    client_id: "your-cognito-app-client-id"
    client_secret: "your-cognito-app-client-secret"
    user_pool_id: "us-east-1_AbCdEfGhI"
    aws_region: "us-east-1"
```

### oci

Authenticates via Oracle Cloud Infrastructure (OCI) Identity. Requires `config_url`.

```yaml
default:
  auth: "oci"
  oauth:
    base_url: "https://your-mcc-server.example.com"
    client_id: "your-oci-client-id"
    client_secret: "your-oci-client-secret"
    config_url: "https://idcs-your-tenant.identity.oraclecloud.com/.well-known/openid-configuration"
```

### supabase

Authenticates via Supabase Auth. Requires `project_url`.

```yaml
default:
  auth: "supabase"
  oauth:
    base_url: "https://your-mcc-server.example.com"
    project_url: "https://your-project-ref.supabase.co"
```

### scalekit

Authenticates via ScaleKit. Requires `environment_url` and `resource_id`.

```yaml
default:
  auth: "scalekit"
  oauth:
    base_url: "https://your-mcc-server.example.com"
    environment_url: "https://your-env.scalekit.com"
    resource_id: "your-resource-id"
    client_id: "your-scalekit-client-id"
```

### propelauth

Authenticates via PropelAuth using token introspection. Requires `auth_url`, `introspection_client_id`, and `introspection_client_secret`.

```yaml
default:
  auth: "propelauth"
  oauth:
    base_url: "https://your-mcc-server.example.com"
    auth_url: "https://your-tenant.propelauthtest.com"
    introspection_client_id: "your-client-id"
    introspection_client_secret: "your-client-secret"
```

### descope

Authenticates via Descope. Requires `project_id` and `config_url`.

```yaml
default:
  auth: "descope"
  oauth:
    base_url: "https://your-mcc-server.example.com"
    project_id: "P2abc123..."
    config_url: "https://api.descope.com/P2abc123.../.well-known/openid-configuration"
```

### in-memory

FastMCP's built-in in-process OAuth server. Useful for integration testing without an external IdP. Not intended for production use.

!!! warning "Testing only"
    Tokens are stored in memory and lost on restart. Do not use in production.

```yaml
default:
  auth: "in-memory"
  oauth:
    base_url: "https://your-mcc-server.example.com"
```

---

## Generic OIDC Backend (`jwt`)

For any OIDC-compliant identity provider — Keycloak, Authentik, Okta, Dex, or any IdP that exposes a JWKS endpoint. MCC acts as a pure resource server: the IdP issues tokens, MCC verifies them.

```yaml
default:
  auth: "jwt"
  jwt:
    jwks_uri: "https://your-idp.example.com/.well-known/jwks.json"
    issuer: "https://your-idp.example.com/"
    audience: "your-client-id-or-api-identifier"
    authorization_server: "https://your-idp.example.com/"
    base_url: "https://your-mcc-server.example.com"
    required_scopes: ["openid", "email"]
```

Or via environment variables: `MCC_JWT__JWKS_URI`, `MCC_JWT__ISSUER`, `MCC_JWT__AUDIENCE`, `MCC_JWT__AUTHORIZATION_SERVER`, `MCC_JWT__BASE_URL`.

=== "Keycloak"

    ```yaml
    jwt:
      jwks_uri: "https://keycloak.example.com/realms/myrealm/protocol/openid-connect/certs"
      issuer: "https://keycloak.example.com/realms/myrealm"
      audience: "mcc"
      authorization_server: "https://keycloak.example.com/realms/myrealm"
      base_url: "https://your-mcc-server.example.com"
    ```

=== "Authentik"

    ```yaml
    jwt:
      jwks_uri: "https://authentik.example.com/application/o/mcc/jwks/"
      issuer: "https://authentik.example.com/application/o/mcc/"
      audience: "your-client-id"
      authorization_server: "https://authentik.example.com/application/o/mcc/"
      base_url: "https://your-mcc-server.example.com"
    ```

=== "Okta"

    ```yaml
    jwt:
      jwks_uri: "https://your-org.okta.com/oauth2/default/v1/keys"
      issuer: "https://your-org.okta.com/oauth2/default"
      audience: "api://default"
      authorization_server: "https://your-org.okta.com/oauth2/default"
      base_url: "https://your-mcc-server.example.com"
    ```

Identity is resolved from the token's `email` claim. Ensure your IdP includes email in the JWT payload and add users before they connect:

```bash
mcc user add alice --email alice@example.com
```
