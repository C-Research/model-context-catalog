import inspect
import json
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError, create_model, model_validator

from mcc.context import CONTEXT_PARAM, UserModel, current_user_var
from mcc.exec import _build_pyrunner_env, make_exec_callable, make_py_callable
from mcc.settings import logger
from mcc.template import jinja_env


@dataclass
class ToolCallEvent:
    """One completed ToolModel.call() invocation — fired to every on_tool_call hook.

    Only ever produced when the underlying callable actually ran (success or
    error) — a call vetoed by rate limiting, denied by authorization, cancelled
    during elicitation, or served from execute()'s result cache never reaches
    ToolModel.call() and therefore never produces one of these.
    """

    tool_key: str
    user: "UserModel"
    key_prefix: str | None
    params: dict[str, Any]
    started_at: float
    duration: float
    status: str  # "success" | "error"
    error: str | None = None


_call_hooks: list[Callable[[ToolCallEvent], Awaitable[None]]] = []


def on_tool_call(fn: Callable[[ToolCallEvent], Awaitable[None]]):
    """Registers a hook fired once per ToolModel.call() invocation, on both success and failure."""
    _call_hooks.append(fn)
    return fn


async def _fire_call_hooks(event: ToolCallEvent) -> None:
    """Best-effort: a failing hook is logged and never propagates to the caller."""
    for hook in _call_hooks:
        try:
            await hook(event)
        except Exception:  # noqa: BLE001
            logger.exception("tool-call hook %r failed for %s", hook, event.tool_key)

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
    env_passthrough: bool | list[str] = False
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
        if self.fn is None or self.python is None:
            # Guaranteed by validate_fn_or_exec, which runs first: fn is set
            # whenever exec isn't, and python is set whenever fn is.
            raise RuntimeError("ToolModel invariant violated: fn/python unset with no exec")
        # Introspect whenever params or return_type is unset — an entry with
        # explicit params still needs a subprocess round-trip to learn the
        # function's return_type, but must not have its declared params
        # overwritten.
        if self.params is None or not self.return_type:
            pyrunner_path = str(Path(__file__).with_name("pyrunner.py"))

            effective_cwd = self.cwd if self.cwd is not None else os.getcwd()
            run_kwargs: dict = {
                "capture_output": True,
                "text": True,
                "timeout": 30,
                "cwd": effective_cwd,
                "env": _build_pyrunner_env(
                    self.env, self.env_file, self.env_passthrough, effective_cwd
                ),
            }
            result = subprocess.run(  # nosec B603 -- argv list, no shell; self.python/
                # pyrunner_path are resolved internally and self.fn comes from
                # admin-authored tool YAML, not runtime/caller input
                [self.python, pyrunner_path, "introspect", self.fn],
                check=False,
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
            if self.params is None:
                self.params = [ParamModel(**p) for p in info["params"]]
        if not self.name:
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
        return [
            param
            for param in (self.params or [])
            if not param.has_override and not (self.fn and param.name == CONTEXT_PARAM)
        ]

    @property
    def hidden_params(self):
        return [
            param
            for param in (self.params or [])
            if param.has_override and not (self.fn and param.name == CONTEXT_PARAM)
        ]

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
        if self.fn is None or self.python is None:
            # Guaranteed by validate_fn_or_exec, which runs first: fn is set
            # whenever exec isn't, and python is set whenever fn is.
            raise RuntimeError("ToolModel invariant violated: fn/python unset with no exec")
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

    def allows(self, user: "UserModel") -> bool:
        """Returns True if a user can access this tool"""
        from mcc.auth import can_access

        return can_access(user, self)

    async def call(self, **kwargs: Any) -> Any:
        """
        Executes a tool with given kwarg parameters.
        Any tool overriden params will be forced
        If its async it will be awaited

        Fires one ToolCallEvent to every on_tool_call hook per invocation —
        including a parameter-validation failure, not just a failure of the
        callable itself — carrying the caller's identity and visible params
        only (hidden/override values forced in below are never included; on
        a validation failure, before params are even known, params is empty).
        """
        user = current_user_var.get()
        key_prefix = user.key["prefix"] if user.key else None
        started_at = time.time()
        start = time.perf_counter()
        status, error = "success", None
        visible_values: dict[str, Any] = {}
        try:
            validated = self.param_model(**kwargs)
            call_kwargs = validated.model_dump()
            for param in self.hidden_params:
                call_kwargs[param.name] = param.override
            visible_values = {p.name: call_kwargs[p.name] for p in self.visible_params}

            result = self.callable(**call_kwargs)
            if inspect.isawaitable(result):
                result = await result
            return result
        except ValidationError as exc:
            status, error = "error", f"{type(exc).__name__}: {exc}"
            raise
        except Exception as exc:
            status, error = "error", f"{type(exc).__name__}: {exc}"
            logger.exception("Error calling %s with %s: %s", self.key, kwargs, exc)
            raise
        finally:
            await _fire_call_hooks(
                ToolCallEvent(
                    tool_key=self.key,
                    user=user,
                    key_prefix=key_prefix,
                    params=visible_values,
                    started_at=started_at,
                    duration=time.perf_counter() - start,
                    status=status,
                    error=error,
                )
            )
