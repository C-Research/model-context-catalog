## Why

LLM clients calling MCC tools have no way to inspect the Python code backing `fn`-based tools, or any other Python object already importable in the server's interpreter — they can only see what a tool's YAML `description`/`params` expose. Adding read-only introspection tools (docstrings, source, signatures, module contents, class hierarchy, file location) gives an LLM client context on the codebase it's operating in, the same way a human developer would use `pydoc`/`inspect`/an IDE's "go to definition" while working in this repo.

## What Changes

- Add a new contrib toolset `toolsets/contrib/pysrc.py` + `toolsets/contrib/pysrc.yaml` providing six read-only introspection tools, all in the `admin.dev` group:
  - `get_docstring(fn_path)` — docstring of a module/class/function
  - `get_source(fn_path)` — source code of a module/class/function
  - `get_signature(fn_path)` — parameters (name/type/required/default) and return type of a function/method
  - `list_members(module_path, kind="all")` — a module's top-level functions/classes with a one-line doc summary each, filterable by `kind`
  - `get_class_hierarchy(fn_path)` — a class's MRO/bases and direct subclasses
  - `get_file_location(fn_path)` — source file path and line range of a module/class/function
- Every function identifies its target via a dotpath (`module.attr` or `module:attr.attr`), resolved by importing `mcc.pyrunner.resolve` — the same resolver `fn`-based tools already use — rather than duplicating dotpath-parsing logic.
- Introspection happens in-process, against the server's own interpreter only. There is no equivalent of `fn` tools' per-tool `python:` interpreter override; an operator wanting to introspect a different interpreter/venv can write their own YAML pointing `pysrc.py`'s functions at that interpreter the same way any other fn tool does.
- Register `toolsets/contrib/pysrc.yaml` in `toolsets/contrib/settings.yaml`'s `tools:` list.
- Add `toolsets/contrib/tests/test_pysrc.py` following the existing contrib test pattern (autouse fixture loads the YAML, tools invoked through `mcc.app.execute`).

## Capabilities

### New Capabilities
- `pysrc-tools`: read-only Python introspection tools (docstring, source, signature, module member listing, class hierarchy, file location) exposed as MCC contrib tools under the `admin.dev` group.

### Modified Capabilities
(none — this only adds new tools and a settings registration; no existing capability's requirements change)

## Impact

- **Code**: new `toolsets/contrib/pysrc.py`, new `toolsets/contrib/pysrc.yaml`, one new line in `toolsets/contrib/settings.yaml`. No changes to `mcc/` core modules — `mcc.pyrunner.resolve` is imported, not modified.
- **Tests**: new `toolsets/contrib/tests/test_pysrc.py`.
- **Docs**: none in this change (deferred to implementation/follow-up).
- **Security**: these tools can read arbitrary source/docstrings of anything importable in the server process, including other tools' implementation and any installed dependency. Scoping to `admin.dev` (not `public`) is the mitigation, consistent with how `admin.system`/`admin.shell` gate similarly-powerful introspection/execution tools.
