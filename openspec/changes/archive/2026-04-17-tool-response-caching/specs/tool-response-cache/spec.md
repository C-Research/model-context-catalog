## ADDED Requirements

### Requirement: Tools declare cache TTL in YAML
`ToolModel` SHALL accept an optional `cache_ttl` field (integer, seconds). When absent or `null`, caching is disabled for that tool. Tool authors set this in the tool YAML definition.

#### Scenario: Tool with cache_ttl declared
- **WHEN** a tool YAML entry includes `cache_ttl: 300`
- **THEN** `ToolModel.cache_ttl` equals `300`

#### Scenario: Tool without cache_ttl
- **WHEN** a tool YAML entry omits `cache_ttl`
- **THEN** `ToolModel.cache_ttl` is `None` and no caching occurs for that tool

### Requirement: Execute caches results for tools with cache_ttl
When `tool.cache_ttl` is set, `execute()` SHALL check the cache before calling `tool.call()` and store the result after a cache miss.

#### Scenario: Cache miss — result stored
- **WHEN** `execute()` is called for a tool with `cache_ttl=300` and no cached result exists
- **THEN** `tool.call()` is invoked, the result is stored in the cache with a 300-second TTL, and the result is returned

#### Scenario: Cache hit — tool not called
- **WHEN** `execute()` is called for a tool with `cache_ttl` and a cached result exists for the same key and params
- **THEN** the cached result is returned without calling `tool.call()`

#### Scenario: No cache_ttl — tool always called
- **WHEN** `execute()` is called for a tool without `cache_ttl`
- **THEN** `tool.call()` is always invoked regardless of any prior results

### Requirement: Execute cache key includes tool key and params hash
The cache key for tool execution SHALL be `exec:{tool.key}:{params_hash}` where `params_hash` is the first 16 hex characters of the SHA-256 of the JSON-serialized params dict with keys sorted.

#### Scenario: Same params produce same cache key
- **WHEN** `execute()` is called twice with identical params (regardless of dict key order)
- **THEN** both calls use the same cache key

#### Scenario: Different params produce different cache keys
- **WHEN** `execute()` is called with `{"ip": "1.2.3.4"}` and then `{"ip": "5.6.7.8"}`
- **THEN** the two calls use distinct cache keys

### Requirement: Cache backend configured via settings
The cashews backend URI SHALL be read from `settings.cache.backend`. The default SHALL be `"mem://"`. Changing the URI to a Redis address SHALL be the only change needed to switch to a shared cache.

#### Scenario: Default in-memory backend
- **WHEN** `settings.cache.backend` is not set
- **THEN** cashews uses an in-memory backend

#### Scenario: Redis backend via settings
- **WHEN** `settings.cache.backend` is set to `"redis://localhost"`
- **THEN** cashews uses the Redis backend
