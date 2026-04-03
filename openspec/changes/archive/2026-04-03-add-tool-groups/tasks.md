## 1. Loader — parse new YAML format

- [x] 1.1 Update `load_file` to expect a dict root with `tools` key; raise `ValueError` if root is a list or missing `tools`
- [x] 1.2 Extract `group` from root dict in `load_file` (default `None`); return group alongside tool list
- [x] 1.3 Update `Loader.load` to receive group from `load_file` and pass it to `register`
- [x] 1.4 Update `Loader.register` to accept `group: str | None` and store it in the registry entry as `"group"`

## 2. Search — group filter

- [x] 2.1 Add optional `group: str | None = None` parameter to `search()` in `mcc/app.py`
- [x] 2.2 When `group` is provided, filter `loader.items()` to only entries matching that group before query matching
- [x] 2.3 Verify empty-query + group returns all tools in that group (no code change needed if filter runs first — just confirm)

## 3. Migration

- [x] 3.1 Migrate `tools.yaml` from flat list to dict-wrapper format (`tools:` key, no `group` needed for the demo file)
