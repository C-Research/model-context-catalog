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

elasticsearch_url: https://my-es-host.internal:9200
```

## Environment variables

Any setting can be set via environment variable using the `MCC_` prefix. Nested keys use double underscores:

```bash
MCC_AUTH=dev-admin
MCC_ELASTICSEARCH_URL=https://my-es-host.internal:9200
```

Environment variables always override file-based settings.

### `MCC_SETTINGS_FILES`

A semicolon-separated list of additional settings files to load, appended after `settings.local.yaml`. Use this to layer in toolset configs without modifying your local overrides file:

```bash
MCC_SETTINGS_FILES=toolsets/contrib/settings.yaml;toolsets/osint/settings.yaml
```

Each file is merged with `dynaconf_merge: true`, so `tools` lists are additive.

### `MCC_TOOL_FILES`

A semicolon-separated list of tool YAML files, directories, or glob patterns to load in addition to those declared in `settings.tools`. Use this to inject extra tools at load time without modifying settings files:

```bash
MCC_TOOL_FILES=/etc/mcc/tools;/opt/custom/*.yaml
```

Paths are resolved exactly like entries in the `tools` setting — directories load all `*.yaml` files (flat), and glob patterns expand recursively. These tools are loaded after the settings-declared tools and participate in hot-reload.

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

### Search backend

`search_backend` (env var `MCC_SEARCH_BACKEND`) selects which storage/search engine `UsersIndex`, `KeysIndex`, and `ToolIndex` use. It's read once at process start — not switchable at runtime.

| Key | Default | Description |
|-----|---------|-------------|
| `search_backend` | `elasticsearch` | `elasticsearch` or `opensearch` |

```yaml
search_backend: opensearch
opensearch_url: https://opensearch-user:pass@host:9200?verify_certs=false
```

Switching to `opensearch` requires installing the `opensearch` extra:

```bash
uv sync --extra opensearch
```

See [Elasticsearch](#elasticsearch) and [OpenSearch](#opensearch) below for backend-specific connection settings — `user_index`/`tool_index`/`key_index` are shared across both backends.

### Elasticsearch

The connection is configured with a single `elasticsearch_url` (env var `MCC_ELASTICSEARCH_URL`). Scheme, host, port, and basic-auth credentials all come from the URL:

```
MCC_ELASTICSEARCH_URL=https://elastic:pass@host:9200?verify_certs=false
```

Append `?verify_certs=false` to allow self-signed/untrusted certificates over `https` (dev only).

| Key | Default | Description |
|-----|---------|-------------|
| `elasticsearch_url` | `http://localhost:9200` | Full connection URL, including any `user:password@` and optional `?verify_certs=false` |
| `user_index` | `mcc-users` | Index name for user records |
| `tool_index` | `mcc-tools` | Index name for tool embeddings |
| `key_index` | `mcc-keys` | Index name for API key records |

### OpenSearch

Used when `search_backend: opensearch`. The connection is configured the same way as Elasticsearch — a single `opensearch_url` (env var `MCC_OPENSEARCH_URL`) carrying scheme, host, port, and basic-auth credentials:

```
MCC_OPENSEARCH_URL=https://admin:pass@host:9200?verify_certs=false
```

| Key | Default | Description |
|-----|---------|-------------|
| `opensearch_url` | `http://localhost:9200` | Full connection URL, including any `user:password@` and optional `?verify_certs=false` |

`user_index`/`tool_index`/`key_index` (above) apply to both backends. `ToolIndex`'s vector search uses the OpenSearch k-NN plugin (`faiss` engine, falling back to `lucene`) rather than Elasticsearch's native `knn` — see the `opensearch-backend` capability for details. Score scales differ between backends, so a `min_score` tuned for Elasticsearch may need recalibrating after switching.

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

### `debug`

Dev-mode switch. Default: `false`.

```yaml
debug: true
```

When `true`:

- Forces the `mcc` logger to `DEBUG` level, overriding whatever the active environment's `logging.loggers.mcc.level` says.
- Lets full Python tracebacks from failed fn tools (pyrunner subprocesses) pass through to the LLM.

When `false` (default), a failed fn tool's traceback is reduced to just the exception's type and message before being returned, so source file paths, line numbers, and code context are never leaked to the LLM. This does not affect `exec` tools (shell commands), whose stderr is never Python source.

Settable via `MCC_DEBUG=true`. Leave this off in production.
