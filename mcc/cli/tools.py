import asyncio
import json
from typing import Any

import rich_click as click
from rich import print as pretty_print

from mcc.auth import get_user_by_username
from mcc.auth.models import UserModel
from mcc.cli import console, err
from mcc.loader import loader
from mcc.middleware import current_user_var

_CLI_USER = UserModel(username="cli", groups=["admin"])


@click.group()
def tool():
    """Browse and call catalog tools."""


@tool.command("list", aliases=["ls"])
@click.option("-l", "--long", is_flag=True, help="Show full signature")
def tool_list(long):
    """List all registered tools."""
    if long:
        console.print(loader.list_all())
        return
    for key in sorted(loader):
        console.print(key)


@tool.command()
@click.argument("tool")
def info(tool):
    """Prints the signature of a given tool key"""
    tool_obj = loader.get(tool)
    if not tool_obj:
        err(f" tool `{tool}` not found")
        return
    console.print(tool_obj.signature)


@tool.command("call", aliases=["exec", "run"])
@click.argument("tool")
@click.argument("params", nargs=-1)
@click.option("--json", "json_str", default=None, help="JSON object of parameters")
@click.option(
    "--as",
    "as_user",
    default=None,
    metavar="USERNAME",
    help="Call as this user (resolved from the index). Defaults to a synthetic admin.",
)
@click.option(
    "-p", "--pretty", is_flag=True, default=False, help="Pretty print rich output"
)
def tool_call(tool, params, json_str, as_user, pretty):
    """Look up a tool by key and call it.

    Accepts parameters as `key=value` pairs and/or a `--json` blob. Use `--as
    USERNAME` to call as a specific user and exercise their RBAC (otherwise runs
    as a synthetic admin).

    **Examples:**

        mcc tool call admin.list_users

        mcc tool call my.tool name=foo count=3

        mcc tool call my.tool --json '{"name": "foo", "count": 3}'

        mcc tool call public.request url=https://example.com --as ci-bot
    """

    t = loader.get(tool)
    if not t:
        err(f" tool `{tool}` not found in loaded tools: {','.join(loader)}")
        return

    if as_user is None:
        current_user = _CLI_USER
    else:
        current_user = asyncio.run(get_user_by_username(as_user))
        if current_user is None:
            err(f"user `{as_user}` not found")
            return

    kwargs: dict[str, Any] = {}
    if json_str:
        try:
            kwargs.update(json.loads(json_str))
        except json.JSONDecodeError as e:
            err(f"invalid JSON — {e}")

    for p in params:
        if "=" not in p:
            err(f"expected `key=value`, got `{p}`")
            return
        key, _, value = p.rpartition("=")
        kwargs[key] = value

    async def _execute():
        current_user_var.set(current_user)
        if not t.allows(current_user):
            err(f"tool `{tool}` is not accessible to `{current_user.username}`")
            return None
        return await t.call(**kwargs)

    try:
        result = asyncio.run(_execute())
    except Exception as e:
        err(e)
        return

    if isinstance(result, tuple):
        # exception
        console.print(result[1]) if pretty else print(result[1])
        err(result[2], result[0])
        return
    if result is None:
        return
    try:
        result = json.loads(result)
    except (json.JSONDecodeError, ValueError):
        pass
    printer = pretty_print if pretty else print
    printer(result)
