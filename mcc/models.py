import importlib
import inspect
import logging
from typing import Any, Callable
from pydantic import BaseModel, Field, create_model, model_validator

logger = logging.getLogger("mcc.tools")

TYPE_MAP: dict[str, type] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
}

REVERSE_TYPE_MAP: dict[type, str] = {v: k for k, v in TYPE_MAP.items()}


class ParamModel(BaseModel):
    name: str
    type: str = "str"
    required: bool = False
    default: Any = None
    description: str = ""
    override: Any = Field(default_factory=lambda: ...)

    @property
    def has_override(self) -> bool:
        return self.override is not ...

    @model_validator(mode="after")
    def typecheck(self):
        if self.type not in TYPE_MAP:
            raise ValueError(f"Unknown type '{self.type}' for parameter '{self.name}'")
        return self

    @property
    def py_type(self):
        return TYPE_MAP[self.type]


def _params_from_signature(fn: Callable) -> list[ParamModel]:
    """
    Inspects a callable to populate parameters based on inspect annotations
    """
    params: list[ParamModel] = []
    for param in inspect.signature(fn).parameters.values():
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        annotation = param.annotation if param.annotation is not param.empty else str
        has_default = param.default is not param.empty
        params.append(
            ParamModel(
                name=param.name,
                type=REVERSE_TYPE_MAP.get(annotation, "str"),
                required=not has_default,
                default=param.default if has_default else None,
            )
        )
    return params


def fmt_signature(tool: "ToolModel"):
    """
    Formats the signature block of a tool so that an llm can easily understand it
    """
    parts = []
    for param in tool.params:
        if param.has_override:
            continue
        if param.required:
            parts.append(f"{param.name}: {param.type}")
        else:
            parts.append(f"{param.name}?: {param.type} = {param.default}")
    sig = ", ".join(parts)
    ret = ""
    if tool.callable:
        hint = inspect.signature(tool.callable).return_annotation
        if hint is not inspect.Parameter.empty:
            ret = f" -> {getattr(hint, '__name__', str(hint))}"
    desc = f" - {tool.description}" if tool.description else ""
    return f'{tool.key}{desc}\n  execute("{tool.key}", {sig}){ret}'


class ToolModel(BaseModel):
    group: str | None = None
    name: str = ""
    fn: str
    description: str = ""
    params: list[ParamModel] = Field(default_factory=list)
    callable: Callable | None = None

    @model_validator(mode="after")
    def introspect(self):
        """
        Finds __name__ for  name and __doc__ for description if not provided
        """
        self.callable = self.resolve_fn()
        if not self.name:
            self.name = getattr(self.callable, "__name__", self.fn.rpartition(".")[-1])
        if not self.description:
            self.description = getattr(self.callable, "__doc__", "")
        if not self.params:
            self.params = _params_from_signature(self.callable)
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
        obj: Any = importlib.import_module(module_path)
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
            # if param.has_override:
            #     continue
            fields[param.name] = (
                param.py_type,
                ... if param.required else param.default,
            )
        return create_model(f"{self.key}_params", **fields)

    @property
    def signature(self) -> str:
        return fmt_signature(self)

    def can_access(self, user: dict | None) -> bool:
        from mcc.auth import can_access

        return can_access(user, self)

    async def call(self, **kwargs: Any) -> Any:
        """
        Executes a tool with given kwarg parameters

        If its async it will be awaited
        """
        logger.info("Calling %s with %s", self.key, kwargs)
        validated = self.param_model(**kwargs)
        call_kwargs = validated.model_dump()
        for param in self.params:
            if param.has_override:
                call_kwargs[param.name] = param.override
        try:
            result = self.callable(**call_kwargs)
            if inspect.isawaitable(result):
                result = await result
            return result
        except Exception as exc:
            logger.exception("Error calling %s: %s", self.key, exc)
            raise exc
