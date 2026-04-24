---
icon: lucide/settings
---

# Configuration

MCC uses [Dynaconf](https://www.dynaconf.com/) for configuration. Settings are loaded in this order, with later sources taking precedence:

1. `mcc/settings.yaml` — built-in defaults (do not edit)
2. `settings.local.yaml` — your local overrides (not committed)
3. Environment variables with the `MCC_` prefix

## Local overrides

Create `settings.local.yaml` in your project root to override any setting:

```yaml
auth: github
tools:
  - mytools.yaml

elasticsearch:
  host: my-es-host.internal
  port: 9200
```

## Environment variables

Any setting can be set via environment variable using the `MCC_` prefix. Nested keys use double underscores:

```bash
MCC_AUTH=dev-admin
MCC_ELASTICSEARCH__HOST=my-es-host.internal
MCC_ELASTICSEARCH__PORT=9200
```

Environment variables always override file-based settings.

### `MCC_SETTINGS_FILES`

A semicolon-separated list of additional settings files to load, appended after `settings.local.yaml`. Use this to layer in toolset configs without modifying your local overrides file:

```bash
MCC_SETTINGS_FILES=toolsets/contrib/settings.yaml;toolsets/osint/settings.yaml
```

Each file is merged with `dynaconf_merge: true`, so `tools` lists are additive.

## Environments

Dynaconf supports named environments. MCC ships with `development` (debug logging) and `production` (verbose log format, INFO level) profiles. Set the active environment with:

```bash
ENV_FOR_DYNACONF=production
```

Defaults to `development` unless overridden.

## Settings reference

### `auth`

Authentication backend. Default: `dev-admin` (no auth, dev only).

| Value | Description |
|-------|-------------|
| `dev-admin` | No auth — all requests get admin access (dev only) |
| `dev-public` | No auth — all requests get public access |
| `github` | GitHub OAuth |
| `google` | Google OAuth |
| `azure` | Microsoft Entra ID (Azure AD) |
| `auth0` | Auth0 |
| `clerk` | Clerk |
| `discord` | Discord OAuth |
| `workos` | WorkOS AuthKit |
| `aws` | AWS Cognito |
| `oci` | Oracle Cloud Infrastructure Identity |
| `supabase` | Supabase Auth |
| `scalekit` | ScaleKit |
| `propelauth` | PropelAuth |
| `descope` | Descope |
| `in-memory` | FastMCP in-process OAuth (testing only) |
| `jwt` | Generic OIDC / JWKS token verification |

See [Auth Backends](../auth/backends.md) for backend-specific configuration.

### `tools`

List of YAML tool files or directories to load at startup. Default: `[]`.

```yaml
tools:
  - mytools.yaml                  # single file
  - path/to/tools_dir             # all *.yaml files in directory (flat)
  - path/to/tools/**/*.yaml       # glob pattern (recursive supported)
```

### `embedding_model`

The [fastembed](https://github.com/qdrant/fastembed) model used for semantic search. Default: `BAAI/bge-small-en-v1.5`.

```yaml
embedding_model: BAAI/bge-small-en-v1.5
```

The model is downloaded on first use and cached locally by fastembed. Changing this requires a server restart to re-index tools.

### `elasticsearch`

Connection settings for Elasticsearch.

| Key | Default | Description |
|-----|---------|-------------|
| `host` | `localhost` | Hostname |
| `port` | `9200` | Port |
| `scheme` | `http` | `http` or `https` |
| `username` | `""` | Basic auth username |
| `password` | `""` | Basic auth password |
| `user_index` | `mcc-users` | Index name for user records |
| `tool_index` | `mcc-tools` | Index name for tool embeddings |

For API key auth, set `MCC_ELASTICSEARCH__API_KEY` instead of username/password.

### `oauth`

Required for all OAuth proxy backends (`github`, `google`, `azure`, etc.).

| Key | Description |
|-----|-------------|
| `base_url` | Public base URL of the MCC server (used for the OAuth callback) |
| `client_id` | OAuth app client ID |
| `client_secret` | OAuth app client secret |

Some backends require additional keys — see [Auth Backends](../auth/backends.md) for per-provider details. All keys are settable via env vars: `MCC_OAUTH__BASE_URL`, `MCC_OAUTH__CLIENT_ID`, `MCC_OAUTH__CLIENT_SECRET`.

### `jwt`

Required when `auth: jwt` (generic OIDC / JWKS verification).

| Key | Description |
|-----|-------------|
| `jwks_uri` | URL of the IdP's JWKS endpoint |
| `issuer` | Expected token issuer |
| `audience` | Expected token audience |
| `authorization_server` | Authorization server URL |
| `base_url` | Public base URL of the MCC server |
| `required_scopes` | List of scopes that must be present in the token |

### `server`

HTTP server settings.

| Key | Default | Description |
|-----|---------|-------------|
| `transport` | `sse` | MCP transport (`sse` or `stdio`) |
| `host` | `0.0.0.0` | Bind address |
| `port` | `8000` | Listen port |
| `response_max_size` | `5000000` | Maximum tool response size in bytes before truncation |

When a tool response exceeds `response_max_size`, MCC truncates the text content and appends `[Response truncated due to size limit]` rather than returning an error. Override via environment variable:

```bash
MCC_SERVER__RESPONSE_MAX_SIZE=10000000  # 10 MB
```

### `logging`

Standard Python `logging.config.dictConfig` dict. The built-in config writes to stderr. Override the log level per environment or set it directly:

```yaml
logging:
  loggers:
    mcc:
      level: DEBUG
```
