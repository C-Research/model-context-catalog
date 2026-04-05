## 1. Settings

- [x] 1.1 Rename `elasticsearch.index` to `elasticsearch.user_index` in `mcc/settings.yaml`, add `elasticsearch.tool_index: "mcc-tools"`
- [x] 1.2 Update `UsersIndex.index` in `mcc/auth/db.py` to read `settings.ELASTICSEARCH.USER_INDEX`
- [x] 1.3 Update `conftest.py` to set `MCC_ELASTICSEARCH__USER_INDEX` and `MCC_ELASTICSEARCH__TOOL_INDEX` test env vars (remove old `MCC_ELASTICSEARCH__INDEX`)

## 2. ToolIndex

- [x] 2.1 Create `mcc/tool_db.py` with `ToolIndex(ESIndex)` class; set `index = settings.ELASTICSEARCH.TOOL_INDEX`; define ES mapping with `name` (text), `description` (text), `groups` (keyword) only
- [x] 2.2 Implement `ToolIndex.put(tool: ToolModel) -> None` — calls base `put()` with `{"name": tool.name, "description": tool.description, "groups": tool.groups}`, using `tool.key` as document ID
- [x] 2.3 Implement `ToolIndex.search(query, group=None) -> list[str]` — builds `multi_match` query (`fields: [name^2, description]`, `fuzziness: AUTO`), wraps in bool filter on `groups` term if `group` provided, returns list of document IDs (`_id` from hits)

## 3. Loader

- [x] 3.1 Add `async def save(self) -> None` to `Loader` — drops and recreates `ToolIndex`, then calls `put` for all tools in `self.values()`
- [x] 3.2 Make `reload(self)` `async def` — keep existing clear+load logic, add `await self.save()` at the end
- [x] 3.3 Add `async def search(self, query: str, group: str | None = None) -> list[ToolModel]` — calls `ToolIndex.search()` to get keys, resolves each against `self`, skips missing keys

## 4. App & CLI Integration

- [x] 4.1 Add FastMCP lifespan to `mcc/app.py` — `async with` context manager that calls `await loader.save()` on startup; pass to `FastMCP(..., lifespan=lifespan)`
- [x] 4.2 Update `cli()` group in `mcc/cli.py` to call `arun(loader.save())` before subcommands run
- [x] 4.3 Update `search` MCP tool in `mcc/app.py` — replace dict iteration with `results = await loader.search(query, group)`, filter with `can_access`, format and return

## 5. Tests

- [x] 5.1 Add `_fresh_tool_index` pytest fixture (non-autouse) — drops/creates `ToolIndex`, calls `await loader.save()`, drops on teardown
- [x] 5.2 Write tests for `ToolIndex`: `put` (verify stored fields), `search` (name match, description match, group filter, fuzzy, no results)
- [x] 5.3 Write tests for `Loader.save()` — verifies ES reflects dict contents; verifies stale tools removed after reload
- [x] 5.4 Write tests for `Loader.search()` — returns full ToolModels resolved from dict; skips keys not in loader
- [x] 5.5 Write tests for updated `search` MCP tool — ES-backed results, access filtering still applied
