## Why

LLM tool catalogs grow large quickly, bloating context windows and degrading model performance. Instead of registering every function as a named MCP tool, mcc exposes just two tools — `search` and `execute` — letting the LLM discover and invoke functions from a YAML-defined catalog at runtime.

## What Changes

- Introduce `tools.yaml` as the authoritative catalog of callable functions
- Add `mcc/loader.py` to eagerly load the catalog, import functions, and build a runtime registry
- Add `mcc/tools.py` to register `search` and `execute` as the only two FastMCP tools
- Update `main.py` to wire loader and FastMCP app together

## Capabilities

### New Capabilities

- `tool-catalog`: YAML-based definition of tools with name, fn path, description, and typed parameters
- `catalog-loader`: Eager loading of tool catalog into a plain dict registry with per-tool Pydantic validation models
- `search-tool`: MCP tool that matches a query against tool names and descriptions, returning compact call-signature info
- `execute-tool`: MCP tool that validates params via Pydantic and dispatches to the registered function

### Modified Capabilities

## Impact

- `main.py`: updated to initialize registry and mount tools on FastMCP app
- New files: `tools.yaml`, `mcc/loader.py`, `mcc/tools.py`
- Dependencies: `fastmcp`, `pydantic`, `pyyaml`
