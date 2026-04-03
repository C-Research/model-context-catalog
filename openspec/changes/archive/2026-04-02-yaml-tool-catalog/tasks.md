## 1. Project Setup

- [x] 1.1 Add `pyyaml` to `pyproject.toml` dependencies
- [x] 1.2 Create `tools.yaml` at project root with one example tool entry

## 2. Loader

- [x] 2.1 Create `mcc/loader.py` with `TYPE_MAP` constant mapping YAML type strings to Python types
- [x] 2.2 Implement YAML parsing — read `tools.yaml`, validate required fields per entry
- [x] 2.3 Implement function import — use `importlib` to resolve dotted `fn` paths, raise `ImportError` on failure
- [x] 2.4 Build per-tool Pydantic model using `create_model` — required params use `...`, optional params use their default
- [x] 2.5 Assemble registry dict `{name: {fn, model, description, parameters}}`, raise `ValueError` on duplicate names
- [x] 2.6 Expose `build_registry(path: str) -> dict` as the public API of `loader.py`

## 3. Tools

- [x] 3.1 Create `mcc/tools.py` — accept registry as a parameter, return configured FastMCP app
- [x] 3.2 Implement `search(query: str)` — case-insensitive substring match on name and description, return compact plain-text results with execute call signatures
- [x] 3.3 Implement `execute(name: str, params: dict)` — check name in registry, validate with Pydantic model, call function, return result; return error strings (not exceptions) for unknown tool or validation failure

## 4. Wiring

- [x] 4.1 Update `main.py` to call `build_registry("tools.yaml")` and pass registry into tool registration
- [x] 4.2 Verify app starts cleanly and both tools are visible via FastMCP
