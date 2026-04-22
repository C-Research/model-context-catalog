## Context

The `isolated-python-interpreter` change introduced `pyrunner.py` and `make_py_callable` as an opt-in subprocess path for fn tools with an explicit `python:` field. The remaining in-process path (`resolve()` + `params_from_signature()` + direct call) is now a parallel implementation with a subset of capabilities.

This change makes the subprocess path universal by defaulting `python` to `sys.executable`. The in-process path is deleted entirely.

## Goals / Non-Goals

**Goals:**
- One execution path for all fn tools: pyrunner subprocess
- Batch introspection at load time: one subprocess per unique python interpreter
- Return type annotation surfaced from pyrunner introspect
- No changes required to existing tool YAML files

**Non-Goals:**
- Connection pooling or persistent pyrunner processes (each call still spawns fresh)
- Batching exec calls (exec runs one at a time, unchanged)
- Changing the exec tool path in any way

## Decisions

### 1. python defaults to sys.executable, not None

`ToolModel.python` is resolved in the `validate_fn_or_exec` validator: if `fn` is set and `python` is None, set `self.python = sys.executable`. After validation, `python` is always a non-None absolute path for fn tools. This eliminates the `if self.python` branch throughout.

**Alternative considered**: Keep `python: str | None` and treat `None` as "use sys.executable" implicitly at call time. Rejected — eager resolution is consistent with the existing `shutil.which` behavior and makes the stored model state unambiguous.

### 2. Batch introspection in loader, not ToolModel

The loader pre-pass groups raw YAML entries by their resolved python interpreter and calls:

```
python pyrunner.py introspect fn1 fn2 fn3 ...
```

once per unique interpreter. Results are injected into each raw entry dict (`name`, `description`, `params`, `return_type`) before `ToolModel` construction. The ToolModel `introspect` validator checks `if not self.params` — pre-populated entries skip the subprocess.

This means direct `ToolModel` construction (e.g. in tests) still works: if `params` are not supplied, ToolModel spawns its own introspect subprocess for that single fn. The batch optimization is purely a loader concern.

**Alternative considered**: Move batching into ToolModel via a class-level registry. Rejected — too much magic. The loader already iterates all entries before constructing models; it's the natural place for a pre-pass.

### 3. pyrunner introspect: variadic fn_paths, JSON array output, per-item errors

```
# invocation
python pyrunner.py introspect fn_path [fn_path ...]

# stdout
[
  {"fn_path": "...", "name": "...", "doc": "...", "params": [...], "return_type": "str"},
  {"fn_path": "...", "error": "ImportError: no module named 'x'"}
]
```

Per-item errors allow a partial batch to succeed. Single-fn invocations (from ToolModel direct construction) return a one-element array; the caller takes `result[0]`.

Within a single batch call, introspection runs in two phases to fail as fast as possible:

```
Phase 1 — resolve all fn_paths
  for each fn_path:
    try: resolve(fn_path)          # importlib.import_module + getattr chain
    except: record error, continue

Phase 2 — inspect successfully resolved fns
  for each fn that resolved:
    try: inspect.signature(fn), getdoc, return annotation
    except: record error, continue
```

Import errors (the most common failure — wrong module path, missing package, bad dynaconf config) are surfaced in phase 1 before any inspection work begins. Phase 2 only runs on fns that are already confirmed importable. Both phases record per-item errors with full tracebacks; neither raises — the caller sees the complete picture in one pass.

Each failure entry carries the full traceback captured from `sys.stderr` within the subprocess:
```json
{"fn_path": "atlas.db:get_labels", "error": "Traceback (most recent call last):\n  ..."}
```

The loader re-raises these with a message that includes the tool's fn path, the source YAML file, and the full error text:
```
Failed to load tool 'atlas.db:get_labels' from atlas.yaml:
Traceback (most recent call last):
  File ".../pyrunner.py", line 62, in introspect
    fn = resolve(fn_path)
  ...
AttributeError: 'Settings' object has no attribute 'LOGGING'
```

This covers the full failure surface: import errors, missing attributes, errors raised during `inspect.signature()` (e.g. a descriptor that raises on access), and any other exception in the introspect path.

**Alternative considered**: Return a dict keyed by fn_path. Rejected — array preserves order and is simpler to consume when the caller already has the ordered list.

### 4. return_type field

pyrunner resolves the return annotation:
```python
hint = inspect.signature(fn).return_annotation
return_type = None if hint is inspect.Parameter.empty else str(hint)
```

`str(hint)` handles both simple names (`"str"`) and generic aliases (`"list[str]"`, `"dict[str, Any]"`).

ToolModel gains `return_type: str | None`. The `signature` property uses it instead of `inspect.signature(self.callable).return_annotation` — which was already broken for the subprocess path since `self.callable` is `_exec`, not the actual function.

### 5. Drop params_from_signature and resolve import

`params_from_signature()` and the `resolve` import in `models.py` become dead code once the in-process path is removed. Both are deleted. `resolve` remains in `pyrunner.py` where it belongs.

### 6. Loader pre-pass only for fn+python entries

Only entries with `fn` set (after resolving python default) participate in batch introspection. `exec` entries and fn entries with explicit `params` skip the pre-pass entirely. The pre-pass does not change load order or registration behavior.

## Risks / Trade-offs

**Subprocess overhead for previously-in-process tools** → Contrib tools (`toolsets.contrib.*`) and any fn tool that previously ran in-process now pays subprocess overhead at load time (one batch call for all tools sharing `sys.executable`). At call time, each invocation still spawns a fresh process. For typical catalog sizes this is acceptable; the batch call amortizes load cost.

**sys.executable may differ from the mcc venv python** → In normal operation `sys.executable` is the venv python, which has all contrib dependencies. In unusual setups (e.g. running mcc with a bare python) contrib tools may fail to import. This was already possible with explicit `python:` fields; now it applies universally.

**Per-item error granularity** → If one fn in a batch fails to introspect, others in the same batch succeed. The loader must handle mixed results cleanly.
