import importlib
import inspect
from typing import Any, Callable
from pydantic import BaseModel, Field, create_model, model_validator

TYPE_MAP: dict[str, type] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
}


class ParamModel(BaseModel):
    name: str
    type: str = "str"
    required: bool = False
    default: Any = None
    description: str = ""

    @model_validator(mode="after")
    def typecheck(self):
        if self.type not in TYPE_MAP:
            raise ValueError(f"Unknown type '{self.type}' for parameter '{self.name}'")
        return self

    @property
    def py_type(self):
        return TYPE_MAP[self.type]


class ToolModel(BaseModel):
    group: str | None = None
    name: str = ""
    fn: str
    description: str = ""
    params: list[ParamModel] = Field(default_factory=list)
    callable: Callable = None

    @model_validator(mode="after")
    def introspect(self):
        self.callable = self.resolve_fn()
        if not self.name:
            self.name = getattr(self.callable, "__name__", self.fn.rpartition(".")[-1])
        if not self.description:
            self.description = getattr(self.callable, "__doc__", "")
        return self

    def resolve_fn(self) -> Callable:
        if ":" in self.fn:
            module_path, attrs = self.fn.split(":", 1)
        else:
            module_path, _, attrs = self.fn.rpartition(".")
        if not module_path or not attrs:
            raise ImportError(
                f"Invalid fn path '{self.fn}': use 'module:attr.attr' or 'module.attr'"
            )
        obj = importlib.import_module(module_path)
        for attr in attrs.split("."):
            obj = getattr(obj, attr)
        return obj

    @property
    def key(self):
        return f"{self.group}.{self.name}" if self.group else self.name

    @property
    def param_model(self) -> type[BaseModel]:
        fields: dict = {}
        for param in self.params:
            fields[param.name] = (
                (param.py_type, ...)
                if param.required
                else (param.py_type, param.default)
            )
        return create_model(f"{self.key}_params", **fields)

    @property
    def signature(self) -> str:
        parts = []
        for param in self.params:
            if param.required:
                parts.append(f"{param.name}: {param.type}")
            else:
                parts.append(f"{param.name}?: {param.type} = {param.default}")
        sig = ", ".join(parts)
        return f'{self.key} — {self.description}\n  execute("{self.key}", {{{sig}}})'

    def can_access(self, user: dict | None) -> bool:
        from .auth import can_access

        return can_access(user, self)

    async def call(self, **kwargs):
        validated = self.param_model(**kwargs)
        result = self.callable(**validated.model_dump())
        if inspect.isawaitable(result):
            return await result
        return result
