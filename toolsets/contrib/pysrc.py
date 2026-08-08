import importlib
import inspect

from mcc.pyrunner import resolve

_TYPE_NAMES: dict[type, str] = {
    str: "str",
    int: "int",
    float: "float",
    bool: "bool",
    list: "list",
    dict: "dict",
}


def get_docstring(fn_path: str) -> str:
    """Return the docstring for a module, class, or function, resolved via dotpath."""
    return inspect.getdoc(resolve(fn_path)) or ""


def get_source(fn_path: str) -> str:
    """Return the source code for a module, class, or function, resolved via dotpath."""
    return inspect.getsource(resolve(fn_path))


def get_signature(fn_path: str) -> dict:
    """Return a function or method's parameters and return type, resolved via dotpath."""
    fn = resolve(fn_path)
    sig = inspect.signature(fn)
    params = []
    for param in sig.parameters.values():
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        annotation = param.annotation if param.annotation is not param.empty else str
        has_default = param.default is not param.empty
        params.append(
            {
                "name": param.name,
                "type": _TYPE_NAMES.get(annotation, "str"),
                "required": not has_default,
                "default": param.default if has_default else None,
            }
        )
    hint = sig.return_annotation
    return_type = (
        None
        if hint is inspect.Signature.empty
        else getattr(hint, "__name__", str(hint))
    )
    return {"params": params, "return_type": return_type}


def list_members(module_path: str, kind: str = "all") -> list[dict]:
    """List a module's own top-level functions/classes with a one-line doc summary.

    Excludes names merely imported into the module (those whose __module__
    doesn't match module_path).
    """
    module = importlib.import_module(module_path)
    wanted = {
        "function": (inspect.isfunction,),
        "class": (inspect.isclass,),
        "all": (inspect.isfunction, inspect.isclass),
    }[kind]

    members = []
    for name, obj in inspect.getmembers(module):
        if name.startswith("__") and name.endswith("__"):
            continue
        if getattr(obj, "__module__", None) != module_path:
            continue
        if not any(check(obj) for check in wanted):
            continue
        doc = inspect.getdoc(obj) or ""
        members.append(
            {
                "name": name,
                "kind": "function" if inspect.isfunction(obj) else "class",
                "doc": doc.splitlines()[0] if doc else "",
            }
        )
    return members


def get_class_hierarchy(fn_path: str) -> dict:
    """Return a class's MRO (bases) and directly known subclasses, resolved via dotpath."""
    cls = resolve(fn_path)

    def qualname(c: type) -> str:
        return f"{c.__module__}.{c.__qualname__}"

    bases = [qualname(c) for c in inspect.getmro(cls) if c is not cls]
    subclasses = [qualname(c) for c in cls.__subclasses__()]
    return {"bases": bases, "subclasses": subclasses}


def get_file_location(fn_path: str) -> dict:
    """Return the source file path and line range for a module, class, or function."""
    obj = resolve(fn_path)
    file = inspect.getsourcefile(obj)
    lines, start = inspect.getsourcelines(obj)
    return {"file": file, "lineno": start, "endlineno": start + len(lines) - 1}
