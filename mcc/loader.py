import importlib
from pathlib import Path
from typing import Any, Callable

import yaml
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


class ToolModel(BaseModel):
    name: str
    fn: str
    description: str
    parameters: list[ParamModel] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_param_types(self):
        for p in self.parameters:
            if p.type not in TYPE_MAP:
                raise ValueError(
                    f"Unknown type '{p.type}' for parameter '{p.name}' in tool '{self.name}'"
                )
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

    def build_param_model(self) -> type[BaseModel]:
        fields: dict = {}
        for p in self.parameters:
            py_type = TYPE_MAP[p.type]
            fields[p.name] = (py_type, ...) if p.required else (py_type, p.default)
        return create_model(f"{self.name}_params", **fields)

    def to_registry_entry(self) -> dict:
        return {
            "fn": self.resolve_fn(),
            "model": self.build_param_model(),
            "description": self.description,
            "parameters": [p.model_dump() for p in self.parameters],
        }


def load_file(path: str | Path) -> tuple[list[ToolModel], str | None]:
    if not isinstance(path, Path):
        path = Path(path)
    if not path.is_file():
        raise ValueError(f"Tool file {path!r} not found")
    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict) or "tools" not in raw:
        raise ValueError(
            f"{path}: expected a dict with a 'tools' key, got {type(raw).__name__}"
        )
    group: str | None = raw.get("group", None)
    return [ToolModel(**entry) for entry in raw["tools"]], group


class Loader(dict):
    def load(self, *paths: str | Path) -> None:
        for path in paths:
            tools, group = load_file(path)
            for tool in tools:
                self.register(tool, group=group)

    def register(self, tool: ToolModel, *, group: str | None = None):
        key = f"{group}.{tool.name}" if group else tool.name
        if key in self:
            raise ValueError(f"Duplicate tool name: {key}")
        entry = tool.to_registry_entry()
        entry["group"] = group
        self[key] = entry


loader = Loader()
