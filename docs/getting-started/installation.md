---
icon: lucide/download
---

# Installation

## Requirements

- Python 3.10+
- Elasticsearch 8.x (for tool indexing and user storage)

## Install

```bash
pip install model-context-catalog
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add model-context-catalog
```

## Elasticsearch

MCC requires a running Elasticsearch instance. The quickest way to get one locally:

```bash
curl -fsSL https://elastic.co/start-local | sh
```

## Configuration

Create a `settings.local.yaml` in your working directory:

```yaml
default:
  elasticsearch:
    dynaconf_merge: true
    api_key: "key provided"
```

See [Auth Backends](../auth/backends.md) for authentication configuration.
