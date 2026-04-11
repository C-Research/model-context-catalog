---
icon: lucide/server
---

# Auth Backends


MCC supports multiple authentication backends. Configure one in `settings.local.toml`.

## GitHub OAuth

Authenticates users via GitHub OAuth 2.0. The GitHub login is used as the username.

!!! warning "Under construction"
    This is a work in progress as OAuth2 providers are still untested 

```toml
[default]
auth = "github_oauth"

[default.github]
client_id = "your-github-app-client-id"
client_secret = "your-github-app-client-secret"
```

Users must exist in the MCC user store. Add them before they connect:

```bash
mcc user add alice --email alice@example.com
```

## GitHub PAT

Authenticates using a GitHub Personal Access Token. MCC calls the GitHub API to resolve the token to a login/email.

```toml
[default]
auth = "github_pat"
```

Clients pass the PAT as a bearer token. MCC resolves it to a GitHub identity, then looks up the user in the store.

## dev-admin

!!! danger "Dev only"
    This mode grants admin access to any request. Do not expose the server publicly when using this backend.

No authentication — automatically selects the first admin user in the database. If no admin user exists, falls back to a dummy user with `groups: [admin]`. **Never use in production.**

```toml
[default]
auth = "dev-admin"
```

Useful for local development and testing without setting up OAuth.

## dev-public


No authentication — automatically selects the first public user in the database. If no public user exists, falls back to a dummy user with `groups: [public]`. 
```toml
[default]
auth = "dev-public"
```

Useful for testing the public tool surface without granting admin access.
OK to use in prod but will be limited to only public tools

