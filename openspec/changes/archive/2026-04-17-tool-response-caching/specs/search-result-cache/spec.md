## ADDED Requirements

### Requirement: Search caches Elasticsearch results with configurable TTL
`loader.search()` SHALL cache the raw Elasticsearch hits (list of `(key, score)` tuples) before user-permission filtering. Caching is enabled when `settings.cache.search_ttl` is greater than zero.

#### Scenario: Cache miss — ES queried and result stored
- **WHEN** `search()` is called with a query that has no cached result and `search_ttl > 0`
- **THEN** `ToolIndex.query()` is called, the hits are stored in the cache with the configured TTL, and the filtered results are returned

#### Scenario: Cache hit — ES not queried
- **WHEN** `search()` is called with a query that has a cached result
- **THEN** `ToolIndex.query()` is not called; the cached hits are used and filtered by user permissions before returning

#### Scenario: search_ttl is zero — caching disabled
- **WHEN** `settings.cache.search_ttl` is `0` or unset
- **THEN** every `search()` call queries Elasticsearch directly

### Requirement: Search cache key includes query and min_score
The search cache key SHALL be `search:{query}:{min_score}` where `min_score` is the string representation of the value (or `"None"` when not provided).

#### Scenario: Same query and min_score reuse cached result
- **WHEN** `search()` is called twice with the same query and min_score
- **THEN** only the first call queries Elasticsearch

#### Scenario: Different min_score produces different cache key
- **WHEN** `search()` is called with the same query but different `min_score` values
- **THEN** each call uses a distinct cache key

### Requirement: Search cache is invalidated on loader reload
`loader.reload()` SHALL delete all search cache entries (matching `"search:*"`) after re-indexing tools to Elasticsearch.

#### Scenario: Reload clears search cache
- **WHEN** `loader.reload()` is called after cached search results exist
- **THEN** the next `search()` call queries Elasticsearch rather than returning the stale cached result
