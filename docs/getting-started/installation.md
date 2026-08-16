---
icon: lucide/download
---

# Installation

Get started quickly using Elasticsearch (the default) or OpenSearch.

## Requirements

- Python 3.10+
- Elasticsearch 8.x (default) or OpenSearch, for tool indexing and user storage — see [Search backend](configuration.md#search-backend) to choose

## Install

```bash
pip install model-context-catalog
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add model-context-catalog
```

## Elasticsearch (default)

MCC requires a running Elasticsearch instance. The quickest way to get one locally:

```bash
curl -fsSL https://elastic.co/start-local | sh
```

!!! tip "Running OpenSearch instead?"
    MCC also supports OpenSearch as the search backend — install `mcc[opensearch]`, set `search_backend: opensearch`, and see [Search backend](configuration.md#search-backend) for the full setup. `docker-compose.opensearch.yaml` in the repo stands up a local instance.

## Configuration

Create a `settings.local.yaml` in your working directory:

```yaml
default:
  elasticsearch_url: "https://elastic:password@localhost:9200?verify_certs=false"
```

See [Search backend](configuration.md#search-backend) for OpenSearch's equivalent, and [Auth Backends](../auth/backends.md) for authentication configuration.
