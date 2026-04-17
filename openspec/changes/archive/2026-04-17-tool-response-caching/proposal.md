## Why

Tool execution (especially OSINT network calls) and Elasticsearch search queries are repeated frequently within LLM sessions but return identical results for the same inputs. Adding opt-in response caching eliminates redundant calls, reduces latency, and lowers load on external services.

## What Changes

- `ToolModel` gains an optional `cache_ttl` field; tools opt in to caching by declaring it in YAML
- A new `mcc/cache.py` module wraps cashews and exposes setup + utilities
- `execute()` in `app.py` checks/sets cache around `tool.call()` when `cache_ttl` is set
- `loader.search()` caches Elasticsearch results with a configurable TTL; cache is busted on `loader.reload()`
- `settings.yaml` gains a `cache:` block for backend URI, prefix, and search TTL
- A new `admin.cache_stats` contrib tool exposes `cache.get_stats()` for observability
- `cashews` added as a core dependency

## Capabilities

### New Capabilities

- `tool-response-cache`: Per-tool opt-in response caching via `cache_ttl` in YAML; results keyed on tool key + params hash
- `search-result-cache`: Elasticsearch search result caching with TTL and reload-triggered invalidation
- `cache-admin`: Admin contrib tool exposing cashews cache statistics

### Modified Capabilities

- `execute-tool`: `execute()` handler gains cache read/write around `tool.call()` when the tool declares `cache_ttl`
- `search-tool`: `loader.search()` gains cache read/write around the ES query

## Impact

- `mcc/models.py`: `ToolModel` gains `cache_ttl: int | None = None`
- `mcc/cache.py`: new module — cashews setup, `params_hash()` utility
- `mcc/app.py`: `execute()` wraps `tool.call()` with cache get/set
- `mcc/loader.py`: `search()` wraps `ToolIndex.query()` with cache get/set; `reload()` busts search cache
- `mcc/settings.yaml`: new `cache:` block with `backend`, `prefix`, `search_ttl`
- `mcc/contrib/`: new `cache.yaml` + `cache.py` admin tool
- `pyproject.toml`: adds `cashews` dependency
