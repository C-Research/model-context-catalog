## Context

MCC's contrib toolsets (`toolsets/contrib/*.py`) are plain Python modules with no `mcc` imports beyond narrow, dependency-light helpers (`cache.py` imports `mcc.cache`; everything else is stdlib/third-party only). `mcc/pyrunner.py` already defines the canonical dotpath convention (`module.attr` / `module:attr.attr`) via its `resolve()` function, used both for `fn`-based tool resolution and its own `introspect`/`exec` subcommands. `pyrunner.py` is deliberately stdlib-only so it can run in arbitrary target interpreters, but nothing prevents `mcc`-side code — including a contrib toolset running in the main server process — from importing `resolve` from it directly.

This change adds a small, in-process (server-interpreter-only) introspection toolset. There is no subprocess, no target-interpreter selection, and no new external dependency.

## Goals / Non-Goals

**Goals:**
- Reuse `mcc.pyrunner.resolve` for dotpath resolution rather than re-implementing it, so the convention (and its error messages) stay identical to what `fn` tool authors already see.
- Keep each of the six tools a small, independent function using only `inspect`/stdlib — no shared internal abstraction beyond `resolve`.
- Match the existing contrib module shape exactly: a plain `.py` module of functions with docstrings, paired with a `.yaml` declaring `groups: [admin, dev]` and one entry per function, registered in `toolsets/contrib/settings.yaml`.

**Non-Goals:**
- No cross-interpreter/cross-venv introspection (no `python:` field support). An operator wanting that writes their own YAML pointing at `pysrc.py`'s functions with a different interpreter, same as any other `fn` tool — this toolset's code doesn't need to know about that case.
- No AST-based/no-import introspection (e.g. reading a `.py` file that isn't importable, or scanning a directory tree for definitions). Everything here requires the target to already be importable in the running server process, same precondition `fn` tools already have.
- No caching of introspection results — these are cheap, synchronous, in-process `inspect` calls with no I/O beyond reading already-loaded module source files.

## Decisions

**1. Resolution: import `resolve` from `mcc.pyrunner`, don't reimplement it.**
`mcc/pyrunner.py`'s `resolve(fn_path)` already handles both `module.attr` and `module:attr.attr` forms and raises `ImportError` with a clear message on a malformed path. `pysrc.py` calls it directly (`from mcc.pyrunner import resolve`). This is safe here specifically because `pysrc.py` runs in-process in the main server interpreter (unlike `pyrunner.py` itself, which must stay stdlib-only to run in arbitrary target interpreters) — `pysrc.py` is free to import `mcc.pyrunner` and, transitively, whatever `mcc` needs.

**2. Errors propagate as raised exceptions, not caught and wrapped.**
If `resolve()` raises `ImportError` (bad path) or `inspect.getsource()` raises `OSError`/`TypeError` (e.g. target is a builtin or C-extension with no retrievable source), the function lets it propagate. This matches the existing contrib pattern (see `fs.py`'s `move`/`stat` raising `FileNotFoundError`/`ValueError` directly) — MCC's tool execution layer already turns exceptions into error results for the caller; there's no need for per-tool try/except here.

**3. `get_signature` reimplements the param-extraction loop from `pyrunner.introspect`, not shared code.**
`pyrunner.introspect`'s per-parameter logic (skip `*args`/`**kwargs`, map annotation to a `_TYPE_NAMES` string, compute `required`/`default`) lives in stdlib-only `pyrunner.py` and is coupled to that module's JSON-envelope output format. Rather than extracting a shared helper (which would touch `pyrunner.py`'s stdlib-only constraint for a six-function toolset's benefit), `get_signature` re-derives the same fields directly from `inspect.signature()`, returning a plain dict rather than pyrunner's JSON-array-of-dicts convention. The two implementations solving the same small problem twice is judged cheaper than adding a shared-code seam to a file whose whole design goal is minimal, stdlib-only surface area.

**4. `list_members` uses `inspect.getmembers` filtered to objects defined in (not merely imported into) the target module.**
`inspect.getmembers(module)` returns everything bound in the module's namespace, including re-exported imports. Filtering to `obj.__module__ == module.__name__` (where applicable) keeps results limited to things actually defined there, avoiding a module like `mcc.db` listing every name it happens to import at the top (`AsyncElasticsearch`, `TextEmbedding`, etc.) as if they were part of it.

**5. `get_class_hierarchy`'s "direct subclasses" uses `cls.__subclasses__()`.**
This only finds subclasses that have been imported/defined somewhere already loaded into the process — it cannot discover subclasses in modules never imported. That's an accepted, inherent limitation of runtime introspection (documented in the spec scenario), not something this design works around.

## Risks / Trade-offs

- **[Risk] Exposes full source of anything importable in the process, including other tools' implementations and dependency internals** → mitigated by `admin.dev` group scoping only (no other guardrail); same trust model as `admin.shell`/`admin.system`, which are equally powerful. Documented in the proposal's Impact section.
- **[Trade-off] `get_signature` duplicates ~15 lines of logic already in `pyrunner.py`** → accepted per decision 3; the alternative (shared helper) would require either loosening `pyrunner.py`'s stdlib-only constraint or awkwardly importing from it in a way that returns JSON-shaped output where a plain dict is more natural here.
- **[Risk] `inspect.getsource`/`inspect.getsourcelines` fail for objects without retrievable source (builtins, C extensions, dynamically-created classes)** → accepted; the exception propagates to the caller as the tool's error result, same as any other contrib tool's failure mode.
