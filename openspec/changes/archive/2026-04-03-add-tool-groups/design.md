## Context

The tool catalog currently loads YAML files as bare lists of tool entries. There is no concept of grouping — all tools exist in a flat namespace. This change introduces a file-level `group` field and makes search group-aware.

Current YAML format (bare list):
```yaml
- name: echo
  fn: mcc.example.echo
  description: ...
```

New YAML format (dict wrapper):
```yaml
group: ops          # optional; null/absent = ungrouped
tools:
  - name: echo
    fn: mcc.example.echo
    description: ...
```

## Goals / Non-Goals

**Goals:**
- Tools carry a `group` field (`str | None`) in the registry
- File-level `group` key applies to all tools in the file
- `search` accepts an optional `group` parameter; filters registry before query matching
- Old flat-list YAML format rejected at startup with a clear error

**Non-Goals:**
- Per-tool group overrides (group is file-level only)
- Multiple groups per tool
- Group management endpoints (create/list/delete groups explicitly)
- Inferring group from filename or directory

## Decisions

### Dict-wrapper format is mandatory (no dual-format support)
The old flat-list format is rejected at load time. `tools.yaml` must be migrated.

**Why**: Supporting two formats adds branching in `load_file` and leaks into test surface. This is an early-stage project with one YAML file — a clean break is cheaper than indefinite compatibility shims.

**Alternative considered**: Accept both formats, detect by checking `isinstance(raw, list)`. Rejected because it normalizes the old format as valid, which slows down future additions to the root dict.

### Group stored as `str | None` in registry entry
Each registry entry gains `"group": str | None`. `None` means ungrouped.

**Why**: Explicit `None` is unambiguous — distinct from an empty string or a missing key. Consumers can check `entry["group"] is not None` cleanly.

### Search filters group first, then runs query match
When `group` is provided, the registry is filtered to that group before query matching runs.

**Why**: Minimizes the scan — no point matching query strings against tools the caller doesn't want. Also allows `search(query="", group="ops")` to return all tools in a group efficiently.

### Empty query with group returns all tools in that group
`search(query="", group="ops")` is a valid and useful call — returns every tool in the group.

**Why**: There's no reason to require a query when the caller already knows which group they want. Consistent with the existing behavior where an empty query would match every tool name and description.

## Risks / Trade-offs

- **Breaking change to YAML format** → any external `tools.yaml` files must be migrated. Mitigation: clear startup error message pointing to the new format.
- **Registry entry dict shape changes** → consumers reading `loader[name]` directly gain a new `"group"` key. Not a problem today (no external consumers), but worth noting.

## Migration Plan

1. Update `load_file` to expect dict root
2. Update `Loader.register` to accept and store group
3. Update `search()` signature and filtering logic
4. Migrate `tools.yaml` to new format
5. Update existing specs to reflect new requirements
