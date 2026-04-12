import ast
import asyncio
import json

import rich_click as click
from rich import print as pretty_print

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


@tool.command("call", aliases=["exec"])
@click.argument("tool")
@click.argument("params", nargs=-1)
@click.option("--json", "json_str", default=None, help="JSON object of parameters")
@click.option(
    "-p", "--pretty", is_flag=True, default=False, help="Pretty print rich output"
)
def tool_call(tool, params, json_str, pretty):
    """Look up a tool by key and call it.

    Accepts parameters as `key=value` pairs and/or a `--json` blob.

    **Examples:**

        mcc tool call admin.list_users

        mcc tool call my.tool name=foo count=3

        mcc tool call my.tool --json '{"name": "foo", "count": 3}'
    """

    t = loader.get(tool)
    if not t:
        err(f" tool `{tool}` not found in loaded tools: {','.join(loader)}")
        return

    kwargs: dict = {}
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
        current_user_var.set(_CLI_USER)
        if not t.allows(_CLI_USER):
            err(f"tool `{tool}` is not accessible")
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
    try:
        result = json.loads(result)
    except (json.JSONDecodeError, ValueError):
        pass
    printer = pretty_print if pretty else print
    printer(result)


@tool.command("test")
@click.argument("tool")
@click.option(
    "-p", "--pretty", is_flag=True, default=False, help="Pretty print rich output"
)
def tool_test(tool, pretty):
    """Execute a tool using its example parameters.

    Parses the `example` field from the tool definition and calls the tool
    with those kwargs — useful for smoke-testing a tool after adding it.

    **Example:**

        mcc tool test admin.create_user
    """
    t = loader.get(tool)
    if not t:
        err(f" tool `{tool}` not found in loaded tools: {','.join(loader)}")
        return

    if not t.example:
        err(f"tool `{tool}` has no `example` defined")
        return

    try:
        tree = ast.parse(t.example, mode="eval")
        if not isinstance(tree.body, ast.Call):
            raise ValueError("example is not a function call expression")
        kwargs = {kw.arg: ast.literal_eval(kw.value) for kw in tree.body.keywords}
    except Exception as e:
        err(f"could not parse example `{t.example}` — {e}")
        return

    async def _execute():
        current_user_var.set(_CLI_USER)
        if not t.allows(_CLI_USER):
            err(f"tool `{tool}` is not accessible")
            return None
        return await t.call(**kwargs)

    try:
        result = asyncio.run(_execute())
    except Exception as e:
        err(e)
        return

    if isinstance(result, tuple):
        console.print(result[1]) if pretty else print(result[1])
        err(result[2], result[0])
        return
    try:
        result = json.loads(result)
    except (json.JSONDecodeError, ValueError):
        pass
    printer = pretty_print if pretty else print
    printer(result)
