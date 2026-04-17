## Context

Tool execution in MCC spans Python callables and shell subprocesses, including OSINT tools that make external HTTP calls (crtsh, abuseipdb, virustotal, etc.). These calls are slow, rate-limited, and return deterministic results within a short window. LLM sessions compound this by issuing the same `search()` queries multiple times while probing the catalog.

The current code has no caching layer. Cashews is async-native, supports both in-memory and Redis backends via URI, and integrates cleanly with the existing async codebase.

## Goals / Non-Goals

**Goals:**
- Per-tool opt-in caching via `cache_ttl` in YAML tool definitions
- Search result caching with TTL and reload-triggered invalidation
- Backend configurable via `settings.yaml` (mem:// or Redis URI)
- Admin contrib tool exposing cashews cache stats
- Tests can disable cache via cashews' built-in context manager

**Non-Goals:**
- Stampede protection / background refresh (simple get/set is sufficient for this use case)
- Caching tools that have `None` returns (addressed by sentinel; not a concern in practice with current tools)
- Per-user cache namespacing (search cache is pre-user-filter; execute cache is keyed on params only — override values are YAML constants, not per-user)

## Decisions

### 1. cashews over cachetools or manual asyncio.Lock

cashews is async-native, supports Redis out of the box via URI swap, and has `cache.disable()` for tests. cachetools requires wrapping sync LRU in an async lock manually. Given the project is already fully async, cashews is the right fit.

**Alternative**: `functools.lru_cache` + asyncio wrapper. Rejected — no Redis path, no TTL, poor async ergonomics.

### 2. Programmatic get/set in execute(), not a decorator on ToolModel.call()

TTL is dynamic (varies per tool at runtime). Cashews decorators require a static TTL at decoration time. The programmatic API (`cache.get` / `cache.set`) handles dynamic TTL naturally. `execute()` in `app.py` is the single call site that knows both the tool and its TTL.

**Alternative**: Decorator on `ToolModel.call()`. Rejected — `ToolModel` is a Pydantic model; wiring a per-instance dynamic TTL into a decorator is awkward and leaks cache logic into the model layer.

### 3. Search cache is pre-user-filter

`loader.search()` calls `ToolIndex.query()` (ES + embedding) and then filters results by user permissions in Python. The cache wraps only the ES query result (list of `(key, score)` tuples). User filtering always runs after cache hit. This means the cache is user-agnostic and maximally reusable across different callers issuing the same query.

**Alternative**: Cache the final filtered result keyed on `(query, user_id)`. Rejected — reduces hit rate significantly, complicates invalidation when user permissions change.

### 4. Cache invalidation on reload only

The search cache is invalidated via `cache.delete_match("search:*")` inside `loader.reload()`. No time-based eviction needed for search since the catalog changes only on explicit reload. The `search_ttl` setting acts as a safety net for unexpected staleness, not primary invalidation.

### 5. Sentinel for cache miss

cashews returns `None` for a miss by default. A module-level `_MISS = object()` sentinel is passed as `default` to `cache.get()` to distinguish a legitimate `None` result from a cache miss. This is necessary for tool execution cache; less critical for search (ES never returns None).

### 6. New module: mcc/cache.py

Setup logic and utilities (`params_hash`, `_MISS`) live in `mcc/cache.py`. This keeps cache concerns out of `app.py` and `loader.py`, and provides a single import point for tests to access `cache.disable()`.

```
mcc/cache.py
  cache        ← cashews global instance, configured at startup
  setup()      ← called in app.py lifespan
  params_hash(params) → str   ← sha256[:16] of sorted JSON
  _MISS        ← sentinel object
```

### 7. Cache key format

```
search:{query}:{min_score}          ← ES hits, pre-user-filter
exec:{tool.key}:{params_hash}       ← tool call result
```

Keys are prefixed by cashews with the configured prefix (default: `mcc:`).

### 8. Admin stats tool

A contrib tool `admin.cache_stats` calls `cache.get_stats()` and returns the result. Implemented as a Python `fn` tool in `mcc/contrib/cache.py` + `mcc/contrib/cache.yaml`. Gated to `admin` group, consistent with other admin contrib tools.

## Risks / Trade-offs

- [Stale search results] If a tool is added/removed without calling `reload()`, the search cache may serve stale hits → Mitigated: `search_ttl` is the backstop; `reload()` busts the cache explicitly
- [Stale execute results] A tool whose external data source updates faster than its `cache_ttl` will return stale data → Mitigated: tool authors set TTL; short TTLs (60s) are reasonable defaults for OSINT
- [cashews mem backend is per-process] In multi-worker deployments, each worker has its own cache → Mitigated: swap to Redis backend via config; single-worker deployments are the common case
- [None result ambiguity] A tool returning `None` would always miss the execute cache without the sentinel → Mitigated by `_MISS` sentinel
