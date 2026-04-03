## Context

mcc is a greenfield FastMCP server. The core challenge is keeping the MCP tool surface minimal (just two tools) while making an arbitrary set of Python functions discoverable and callable by an LLM. The registry is the bridge between the static YAML catalog and the runtime dispatch layer.

## Goals / Non-Goals

**Goals:**
- Load `tools.yaml` at startup, fail fast on import errors
- Build a plain dict registry keyed by tool name
- Dynamically construct a Pydantic model per tool for parameter validation
- Expose `search` and `execute` as the only two FastMCP tools
- `search` matches query against name and description, returns compact call-signature text
- `execute` validates params, dispatches to the registered callable, returns result

**Non-Goals:**
- Registering YAML-defined tools as individual MCP tools
- Runtime reloading of the catalog
- Type system beyond `str`, `int`, `float`, `bool`, `list`, `dict`
- Fuzzy/semantic search (substring match on name + description is sufficient)

## Decisions

**`Loader` class subclasses `dict`, module-level singleton**
`Loader` extends `dict` so the registry is the instance itself — `loader[name]` gives the tool entry. A module-level `loader = Loader()` in `loader.py` is imported by both `app.py` (for dispatch) and `main.py` (for loading). This avoids passing the registry around as a parameter.

**Pydantic models built at load time, not at call time**
Each tool gets its `create_model(...)` call during `loader.load()`. Errors surface at startup. At call time, `execute` just does `Model(**params)` — no schema interpretation needed.

**Type mapping defined as a module-level dict in loader.py**
```
TYPE_MAP = {"str": str, "int": int, "float": float, "bool": bool, "list": list, "dict": dict}
```
Unknown types raise a `ValueError` at load time. `type` defaults to `"str"` if omitted from a parameter entry.

**`fn` field is a dotted import path**
e.g. `mcc.weather.get_weather` → `importlib.import_module("mcc.weather")` + `getattr(..., "get_weather")`. Supports any importable module in the Python path. Bare names (no dot) raise `ImportError` immediately.

**Tools registered via `@mcp.tool()` in `app.py`, closing over `loader`**
`search` and `execute` are decorated functions in `mcc/app.py` that close over the module-level `loader` singleton. `main.py` calls `loader.load("tools.yaml")` before `mcp.run()`, ensuring the registry is populated before any tool is called.

**`search` returns plain text, not structured data**
The LLM needs to read the result and derive a call to `execute`. Plain text is more token-efficient and easier for the model to parse than JSON. Format per result:
```
<name> — <description>
  execute("<name>", {param: type, param?: type = default})
```

**`execute` only dispatches to registry entries**
If `name` is not in the registry, return a clear error string. No dynamic import, no fallback.

## Risks / Trade-offs

**Eager import failures block startup** → Acceptable trade-off; surfaces misconfiguration immediately rather than at call time.

**No type coercion in execute** → Pydantic will coerce compatible types (e.g. `"42"` → `int`). Edge cases with `list`/`dict` passed as strings will fail with a validation error returned to the LLM.

**search is substring, not semantic** → The LLM may not find a tool if its query doesn't overlap with the name or description text. Mitigated by writing good descriptions in the catalog.

## Migration Plan

Greenfield — no migration needed. `main.py` is updated to call `build_registry()` from `loader.py` and pass the result into tool registration in `tools.py`.
