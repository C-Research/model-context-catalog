import inspect
import json
import os
import shutil
import subprocess
import sys
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional

from pydantic import BaseModel, Field, create_model, model_validator

from mcc.exec import _build_pyrunner_env, make_exec_callable, make_py_callable
from mcc.settings import logger
from mcc.template import jinja_env

if TYPE_CHECKING:
    from mcc.auth.models import UserModel

TYPE_MAP: dict[str, type] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
}


def sorted_groups(groups: list[str]) -> list[str]:
    """Sorts a list of groups always putting reserved public and admin at the beginning"""
    priority = ["public", "admin"]
    head = [g for g in priority if g in groups]
    tail = [g for g in groups if g not in priority]
    return head + tail


class ParamModel(BaseModel):
    name: str
    type: str = "str"
    required: bool = False
    default: Any = None
    description: str = ""
    example: str = ""
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


class ToolModel(BaseModel):
    groups: list[str] = Field(default_factory=list)
    name: str = ""
    fn: str | None = None
    exec: str | None = Field(default=None, alias="exec")
    curl: str | None = None
    python: str | None = None
    stdin: bool = False
    limits: dict | None = None
    cwd: str | None = None
    env: dict[str, str] | None = None
    env_file: str | None = None
    env_passthrough: bool = False
    transform: str | list[str] | None = None
    cache_ttl: int | None = None
    description: str = ""
    example: str = ""
    params: list[ParamModel] | None = None
    return_type: str | None = None

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def validate_fn_or_exec(self):
        if self.curl:
            if self.fn or self.exec:
                raise ValueError(
                    "Tool must specify only one of 'fn', 'exec', or 'curl'"
                )
            flags = "curl -sL -o -"
            if self.stdin:
                flags += " --json @-"
            # Bare URLs need quoting so shell doesn't interpret & as a background op.
            # Flag-prefixed values (e.g. "-H 'Key: x' 'https://...'") are already quoted.
            curl_arg = (
                f"'{self.curl}'"
                if self.curl.lstrip().startswith(("http://", "https://"))
                else self.curl
            )
            self.exec = f"{flags} {curl_arg}"
        if self.fn and self.exec:
            raise ValueError("Tool must specify either 'fn' or 'exec', not both")
        if not self.fn and not self.exec:
            raise ValueError("Tool must specify either 'fn' or 'exec'")
        if self.python and self.exec:
            raise ValueError("'python' can only be used with 'fn', not 'exec'")
        if self.fn and not self.python:
            self.python = sys.executable
        if self.python:
            resolved = shutil.which(self.python)
            if resolved is None:
                raise ValueError(f"Python interpreter not found: {self.python!r}")
            self.python = resolved
        return self

    @model_validator(mode="after")
    def introspect(self):
        if self.exec:
            if not self.name:
                raise ValueError("Exec tools must specify a 'name'")
            if self.params is None:
                self.params = []
            return self
        assert self.fn is not None
        assert self.python is not None
        if self.params is None:
            pyrunner_path = str(Path(__file__).with_name("pyrunner.py"))

            effective_cwd = self.cwd if self.cwd is not None else os.getcwd()
            run_kwargs: dict = {
                "capture_output": True,
                "text": True,
                "timeout": 30,
                "cwd": effective_cwd,
                "env": _build_pyrunner_env(self.env, self.env_file, False, effective_cwd),
            }
            result = subprocess.run(
                [self.python, pyrunner_path, "introspect", self.fn],
                **run_kwargs,
            )
            if result.returncode != 0:
                raise ValueError(
                    f"Failed to introspect '{self.fn}' with {self.python!r}:"
                    f" {result.stderr}"
                )
            try:
                items = json.loads(result.stdout)
            except (json.JSONDecodeError, ValueError):
                raise ValueError(
                    "Unable to parse JSON output. This is probably because of something in the tool writing to stdout"
                )
            info = items[0]
            if "error" in info:
                raise ValueError(f"Failed to introspect '{self.fn}':\n{info['error']}")
            if not self.name:
                self.name = info["name"]
            if not self.description:
                self.description = info["doc"]
            if not self.return_type:
                self.return_type = info.get("return_type")
            self.params = [ParamModel(**p) for p in info["params"]]
        elif not self.name:
            # params explicitly declared; derive name from path string
            attrs = self.fn.split(":", 1)[-1] if ":" in self.fn else self.fn
            self.name = attrs.rsplit(".", 1)[-1]
        return self

    @property
    def _resolved_transform(self) -> str | None:
        if self.transform is None:
            return None
        if isinstance(self.transform, list):
            return " | ".join(self.transform)
        return self.transform

    @property
    def visible_params(self):
        return [param for param in (self.params or []) if not param.has_override]

    @property
    def hidden_params(self):
        return [param for param in (self.params or []) if param.has_override]

    @property
    def sorted_groups(self):
        return sorted_groups(self.groups)

    @cached_property
    def callable(self) -> Callable:
        if self.exec:
            return make_exec_callable(
                self.exec,
                self.stdin,
                self.limits,
                self.cwd,
                self.env,
                self.env_file,
                self.env_passthrough,
                self._resolved_transform,
            )
        assert self.fn is not None
        assert self.python is not None
        return make_py_callable(
            self.fn,
            self.python,
            self.limits,
            self.cwd,
            self.env,
            self.env_file,
            self.env_passthrough,
            self._resolved_transform,
        )

    @property
    def key(self):
        return ".".join(self.sorted_groups + [self.name])

    @property
    def param_model(self) -> type[BaseModel]:
        fields: dict = {}
        for param in self.visible_params:
            fields[param.name] = (
                param.py_type,
                ... if param.required else param.default,
            )
        return create_model(f"{self.key}_params", **fields)

    @property
    def signature(self) -> str:
        """
        Formats the signature block of a tool as markdown
        """
        return jinja_env.get_template("tool_signature.md").render(tool=self)

    def allows(self, user: Optional["UserModel"]) -> bool:
        """Returns True if a user can access this tool"""
        from mcc.auth import can_access

        return can_access(user, self)

    async def call(self, **kwargs: Any) -> Any:
        """
        Executes a tool with given kwarg parameters.
        Any tool overriden params will be forced
        If its async it will be awaited
        """
        validated = self.param_model(**kwargs)
        call_kwargs = validated.model_dump()
        for param in self.hidden_params:
            call_kwargs[param.name] = param.override
        try:
            result = self.callable(**call_kwargs)
            if inspect.isawaitable(result):
                result = await result
            return result
        except Exception as exc:
            logger.exception("Error calling %s with %s: %s", self.key, kwargs, exc)
            raise exc
