# Auth Backends

!!! warning "Under construction"
    This is a work in progress as this is still alpha software and not tested against any prod OAuth2 providers yet

MCC supports multiple authentication backends. Configure one in `settings.local.toml`.

## GitHub OAuth

Authenticates users via GitHub OAuth 2.0. The GitHub login is used as the username.

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

## Dangerous

!!! danger "Dev only"
    this mode grants admin access to any request. Do not expose the server publicly when using this backend.

No authentication — automatically uses the first admin user in the database. **Never use in production.**

```toml
[default]
auth = "dangerous"
```

Useful for local development and testing without setting up OAuth.

