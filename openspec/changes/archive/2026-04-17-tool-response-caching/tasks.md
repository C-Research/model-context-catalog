## 1. Dependency and settings

- [x] 1.1 Add `cashews` to `pyproject.toml` dependencies
- [x] 1.2 Add `cache:` block to `mcc/settings.yaml` with `backend: "mem://"`, `prefix: "mcc"`, `search_ttl: 60`

## 2. Cache module

- [x] 2.1 Create `mcc/cache.py` with cashews `cache` instance, `setup()` function, `params_hash(params)` utility, and `_MISS` sentinel
- [x] 2.2 Call `cache.setup()` in `app.py` `lifespan` before `loader.save()`

## 3. ToolModel

- [x] 3.1 Add `cache_ttl: int | None = None` field to `ToolModel` in `mcc/models.py`

## 4. Execute caching

- [x] 4.1 In `execute()` in `app.py`, after the `allows()` check, add cache get using `_MISS` sentinel keyed on `exec:{tool.key}:{params_hash(params)}`
- [x] 4.2 After `tool.call()` succeeds, store result in cache with `tool.cache_ttl` as TTL (only when `tool.cache_ttl` is set)

## 5. Search caching

- [x] 5.1 In `loader.search()` in `loader.py`, wrap the `ToolIndex.query()` call with cache get/set using key `search:{query}:{min_score}` and TTL from `settings.cache.search_ttl`
- [x] 5.2 In `loader.reload()`, call `await cache.delete_match("search:*")` after `await self.save()`

## 6. Admin contrib tool

- [x] 6.1 Create `mcc/contrib/cache.py` with a `cache_stats()` async function that returns cache key count and key list
- [x] 6.2 Create `mcc/contrib/cache.yaml` declaring `admin.cache_stats` as a `fn` tool in the `admin` group

## 7. Tests

- [x] 7.1 Add `autouse` fixture to test conftest that clears cache between tests
- [x] 7.2 Add test: tool with `cache_ttl` — first call executes tool, second call returns cached result without calling tool
- [x] 7.3 Add test: tool without `cache_ttl` — tool is called every time
- [x] 7.4 Add test: search caching — second identical search does not call `ToolIndex.query()`
- [x] 7.5 Add test: `loader.reload()` clears search cache

## 8. Docs

- [x] 8.1 Add `cache_ttl` row to the quick reference table in `docs/tools/yaml-format.md`
- [x] 8.2 Add `### cache_ttl` section to `docs/tools/yaml-format.md` under Runtime options, with description and a YAML example showing an OSINT tool opt-in

## 9. Verify

- [x] 9.1 Run `uv run pytest tests/` — all tests pass
- [x] 9.2 Run `uv run ruff check mcc/` — no lint errors
- [x] 9.3 Run `uv run pyright mcc/` — no type errors
