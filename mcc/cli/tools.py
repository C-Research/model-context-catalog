import asyncio
import json

import rich_click as click

from mcc.cli import console, err


@click.group()
def tool():
    """Browse and call catalog tools."""


@tool.command("list")
def tool_list():
    """List all registered tools."""
    from mcc.loader import loader

    md = loader.list_all()
    if not md:
        console.print("[dim]No tools loaded.[/dim]")
        return
    console.print(md)


@tool.command("call")
@click.argument("tool")
@click.argument("params", nargs=-1)
@click.option("--json", "json_str", default=None, help="JSON object of parameters")
def tool_call(tool, params, json_str):
    """Look up a tool by key and call it.

    Accepts parameters as `key=value` pairs and/or a `--json` blob.

    **Examples:**

        mcc tool call admin.list_users

        mcc tool call my.tool name=foo count=3

        mcc tool call my.tool --json '{"name": "foo", "count": 3}'
    """
    from mcc.loader import loader

    t = loader.get(tool)
    if not t:
        err(f" tool `{tool}` not found")

    kwargs: dict = {}
    if json_str:
        try:
            kwargs.update(json.loads(json_str))
        except json.JSONDecodeError as e:
            err(f"invalid JSON — {e}")

    for p in params:
        if "=" not in p:
            err(f"expected `key=value`, got `{p}`")
        key, _, value = p.partition("=")
        kwargs[key] = value

    try:
        result = asyncio.run(t.call(**kwargs))
    except Exception as e:
        err(e)

    if result is not None:
        if isinstance(result, (dict, list)):
            console.print_json(json.dumps(result, default=str))
        else:
            console.print(result)
