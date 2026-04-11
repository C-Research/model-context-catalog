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
auth: github_pat
contrib: true
tools:
  - mytools.yaml

elasticsearch:
  host: my-es-host.internal
  port: 9200
```

## Environment variables

Any setting can be set via environment variable using the `MCC_` prefix. Nested keys use double underscores:

```bash
MCC_AUTH=dangerous
MCC_CONTRIB=true
MCC_ELASTICSEARCH__HOST=my-es-host.internal
MCC_ELASTICSEARCH__PORT=9200
```

Environment variables always override file-based settings.

## Environments

Dynaconf supports named environments. MCC ships with `development` (debug logging) and `production` (verbose log format, INFO level) profiles. Set the active environment with:

```bash
ENV_FOR_DYNACONF=production
```

Defaults to `development` unless overridden.

## Settings reference

### `auth`

Authentication backend. Default: `dangerous` (no auth, dev only).

| Value | Description |
|-------|-------------|
| `dangerous` | No authentication — all requests are anonymous |
| `github_oauth` | GitHub OAuth app flow |
| `github_pat` | GitHub personal access token |

See [Auth Backends](../auth/backends.md) for backend-specific configuration.

### `contrib`

Enable optional built-in tools. Default: `false`.

```yaml
contrib: true
```

See [Contrib Tools](../contrib/index.md) for what's included.

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

### `github_oauth`

Required when `auth: github_oauth`.

| Key | Description |
|-----|-------------|
| `client_id` | GitHub OAuth app client ID |
| `client_secret` | GitHub OAuth app client secret |
| `base_url` | Public base URL of the MCC server (used for the OAuth callback) |

### `github_pat`

Required when `auth: github_pat`.

| Key | Description |
|-----|-------------|
| `token` | GitHub personal access token used to verify caller identity |

### `logging`

Standard Python `logging.config.dictConfig` dict. The built-in config writes to stderr. Override the log level per environment or set it directly:

```yaml
logging:
  loggers:
    mcc:
      level: DEBUG
```
