import asyncio
import json
from typing import Any

import rich_click as click

from mcc.auth import get_user_by_username
from mcc.auth.models import UserModel
from mcc.cli import console, err
from mcc.context import (
    RESERVED_KEYS,
    SLUG_RE,
    assemble_context,
    current_context_var,
    current_user_var,
)
from mcc.loader import loader

_CLI_USER = UserModel(username="cli", groups=["admin"])


def _parse_kv_pairs(pairs: tuple[str, ...]) -> dict[str, Any] | None:
    """Parse `key=value` CLI args into a dict. Prints an error and returns None
    on the first malformed pair."""
    parsed: dict[str, Any] = {}
    for p in pairs:
        if "=" not in p:
            err(f"expected `key=value`, got `{p}`")
            return None
        key, _, value = p.rpartition("=")
        parsed[key] = value
    return parsed


@click.group()
def tool():
    """Browse and call catalog tools."""


@tool.command("list", aliases=["ls"])
@click.option("-l", "--long", is_flag=True, help="Show full signature")
def tool_list(long):
    """List all registered tools."""
    if long:
        console.print(asyncio.run(loader.list_all()))
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
    "--ctx",
    "ctx_vars",
    multiple=True,
    metavar="KEY=VALUE",
    help="Set a context var for this call (repeatable). Available to fn tools "
    "as `context[key]` and to exec tools as MCC_CTX_KEY.",
)
@click.option(
    "--ctx-json",
    "ctx_json_str",
    default=None,
    help="JSON object of context vars (merged with --ctx, --ctx wins on conflict)",
)
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
def tool_call(tool, params, json_str, ctx_vars, ctx_json_str, as_user, pretty):
    """Look up a tool by key and call it.

    Accepts parameters as `key=value` pairs and/or a `--json` blob. Use `--as
    USERNAME` to call as a specific user and exercise their RBAC (otherwise runs
    as a synthetic admin). Use `--ctx`/`--ctx-json` to inject session-style
    context vars for this one call (the same vars a real session would pick up
    via `set_session`).

    **Examples:**

        mcc tool call admin.list_users

        mcc tool call my.tool name=foo count=3

        mcc tool call my.tool --json '{"name": "foo", "count": 3}'

        mcc tool call public.request url=https://example.com --as ci-bot

        mcc tool call my.tool --ctx target_host=10.0.0.5 --ctx budget=100
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

    parsed_params = _parse_kv_pairs(params)
    if parsed_params is None:
        return
    kwargs.update(parsed_params)

    ctx: dict[str, Any] = {}
    if ctx_json_str:
        try:
            ctx.update(json.loads(ctx_json_str))
        except json.JSONDecodeError as e:
            err(f"invalid JSON — {e}")
            return

    parsed_ctx = _parse_kv_pairs(ctx_vars)
    if parsed_ctx is None:
        return
    ctx.update(parsed_ctx)

    for key in ctx:
        if key in RESERVED_KEYS:
            err(f"`{key}` is a reserved identity key and cannot be set via --ctx")
            return
        if not SLUG_RE.match(key):
            err(
                f"invalid context var name `{key}` — must be lowercase letters, "
                "digits, and underscores, not starting with a digit"
            )
            return

    async def _execute():
        current_user_var.set(current_user)
        if not t.allows(current_user):
            err(f"tool `{tool}` is not accessible to `{current_user.username}`")
            return None
        token = current_context_var.set(assemble_context(ctx, current_user))
        try:
            return await t.call(**kwargs)
        finally:
            current_context_var.reset(token)

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
    if pretty:
        console.print_json(data=result)
    else:
        print(json.dumps(result))
