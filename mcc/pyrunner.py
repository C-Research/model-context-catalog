"""
stdlib-only runner for MCC fn-based tools in isolated Python interpreters.

This file MUST NOT import from any mcc module. It is executed directly by
arbitrary Python interpreters (different versions, different venvs) and must
work without mcc or any of its dependencies installed.

Modes:
    python pyrunner.py introspect <fn_path> [fn_path ...]
        Prints JSON array: [{"fn_path": str, "name": str, "doc": str,
                              "params": [...], "return_type": str | null}, ...]
        Each failed entry has {"fn_path": str, "error": str} instead.
        Process always exits 0 so callers can distinguish per-item errors
        from a subprocess crash.

    python pyrunner.py exec <fn_path>
        Reads JSON kwargs from stdin, calls the function, prints JSON result.
"""

import asyncio
import functools
import importlib
import inspect
import io
import json
import sys
import traceback
from typing import Any

_TYPE_NAMES: dict[type, str] = {
    str: "str",
    int: "int",
    float: "float",
    bool: "bool",
    list: "list",
    dict: "dict",
}


def json_handler(fn: Any) -> Any:
    """
    Suppress stdout during fn invocation
    print only its return value to the real stdout.
    """

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> None:
        original_stdout = sys.stdout
        sys.stdout = io.StringIO()
        result = fn(*args, **kwargs)
        json.dump(result, original_stdout, default=str)

    return wrapper


def resolve(fn_path: str) -> Any:
    """Resolve a dotpath or colon-separated fn path to a callable.

    Accepts:
        "module.attr"               e.g. "mypackage.mymodule.my_function"
        "module:attr"               e.g. "mypackage.mymodule:my_function"
        "module:attr.attr"          e.g. "mypackage.mymodule:MyClass.method"
    """
    if ":" in fn_path:
        module_path, attrs = fn_path.split(":", 1)
    else:
        module_path, _, attrs = fn_path.rpartition(".")
    if not module_path or not attrs:
        raise ImportError(
            f"Invalid fn path {fn_path!r}: use 'module:attr.attr' or 'module.attr'"
        )
    obj = importlib.import_module(module_path)
    for attr in attrs.split("."):
        obj = getattr(obj, attr)
    return obj


@json_handler
def introspect(*fn_paths: str) -> str:
    """Inspect functions and print a JSON array of results to stdout.

    Two-phase: resolve all first (catches import errors fast), then inspect.
    Per-item errors include the full traceback. Process exits 0 regardless.
    Side-effect stdout from imports or function bodies is suppressed.
    """
    # Phase 1 — resolve all fn_paths
    resolved: dict[str, Any] = {}
    result_map: dict[str, dict] = {}

    for fn_path in fn_paths:
        try:
            resolved[fn_path] = resolve(fn_path)
        except Exception:
            result_map[fn_path] = {"fn_path": fn_path, "error": traceback.format_exc()}

    # Phase 2 — inspect successfully resolved fns
    for fn_path, fn in resolved.items():
        try:
            sig = inspect.signature(fn)
            params = []
            for param in sig.parameters.values():
                if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                    continue
                annotation = (
                    param.annotation if param.annotation is not param.empty else str
                )
                has_default = param.default is not param.empty
                params.append(
                    {
                        "name": param.name,
                        "type": _TYPE_NAMES.get(annotation, "str"),
                        "required": not has_default,
                        "default": param.default if has_default else None,
                        "description": "",
                    }
                )
            hint = sig.return_annotation
            return_type = (
                None
                if hint is inspect.Parameter.empty
                else getattr(hint, "__name__", str(hint))
            )
            result_map[fn_path] = {
                "fn_path": fn_path,
                "name": getattr(fn, "__name__", fn_path.rsplit(".", 1)[-1]),
                "doc": inspect.getdoc(fn) or "",
                "params": params,
                "return_type": return_type,
            }
        except Exception:
            result_map[fn_path] = {"fn_path": fn_path, "error": traceback.format_exc()}

    return [result_map[fp] for fp in fn_paths]


@json_handler
def execute(fn_path: str) -> str:
    """Read JSON kwargs from stdin, call the function, print JSON result to stdout.

    Side-effect stdout from resolve or the function body is suppressed.
    """
    fn = resolve(fn_path)
    kwargs = json.loads(sys.stdin.read())
    if inspect.iscoroutinefunction(fn):
        return asyncio.run(fn(**kwargs))
    return fn(**kwargs)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "usage: pyrunner.py <introspect|exec> <fn_path> [fn_path ...]",
            file=sys.stderr,
        )
        sys.exit(1)

    _mode = sys.argv[1]

    try:
        if _mode == "introspect":
            introspect(*sys.argv[2:])
        elif _mode == "exec":
            execute(sys.argv[2])
        else:
            print(f"unknown mode: {_mode!r}", file=sys.stderr)
            sys.exit(1)
    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
