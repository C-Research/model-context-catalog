import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import rich_click as click
from pydantic import ValidationError

from mcc.auth import get_user_by_username
from mcc.cli import console, err
from mcc.context import (
    RESERVED_KEYS,
    SLUG_RE,
    UserModel,
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


def _load_json_blob(value: str) -> Any | None:
    """Parse a JSON object from a literal string, or from a file/stdin when
    `value` starts with `@` (curl-style: `@path` reads a file, `@-` reads
    stdin). Prints an error and returns None on failure."""
    if value.startswith("@"):
        path = value[1:]
        try:
            raw = sys.stdin.read() if path == "-" else Path(path).read_text()
        except OSError as e:
            err(f"could not read `{path}` — {e}")
            return None
    else:
        raw = value
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        err(f"invalid JSON — {e}")
        return None


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


@tool.command("reindex")
def tool_reindex():
    """Reload tool YAML files from disk and reindex them in Elasticsearch."""
    asyncio.run(loader.reload())
    console.print(f"[green]Reindexed {len(loader)} tools.[/green]")


@tool.command()
@click.argument("tool")
def info(tool):
    """Prints the signature of a given tool key"""
    tool_obj = loader.get(tool)
    if not tool_obj:
        err(f" tool `{tool}` not found")
        return
    console.print(tool_obj.signature)


def _resolve_caller(as_user: str | None) -> UserModel | None:
    """Resolve the calling user for `tool call`: the given --as username, or a
    synthetic admin when omitted. Prints an error and returns None if the
    username doesn't resolve."""
    if as_user is None:
        return _CLI_USER
    current_user = asyncio.run(get_user_by_username(as_user))
    if current_user is None:
        err(f"user `{as_user}` not found")
    return current_user


def _build_kwargs(json_str: str | None, params: tuple[str, ...]) -> dict[str, Any] | None:
    """Merge a --json blob with key=value CLI params into one kwargs dict.
    Prints an error and returns None on failure."""
    kwargs: dict[str, Any] = {}
    if json_str:
        parsed_json = _load_json_blob(json_str)
        if parsed_json is None:
            return None
        kwargs.update(parsed_json)
    parsed_params = _parse_kv_pairs(params)
    if parsed_params is None:
        return None
    kwargs.update(parsed_params)
    return kwargs


def _build_context_vars(
    ctx_json_str: str | None, ctx_vars: tuple[str, ...]
) -> dict[str, Any] | None:
    """Merge --ctx-json with --ctx key=value pairs and validate each key. Prints
    an error and returns None on failure."""
    ctx: dict[str, Any] = {}
    if ctx_json_str:
        parsed_ctx_json = _load_json_blob(ctx_json_str)
        if parsed_ctx_json is None:
            return None
        ctx.update(parsed_ctx_json)
    parsed_ctx = _parse_kv_pairs(ctx_vars)
    if parsed_ctx is None:
        return None
    ctx.update(parsed_ctx)

    for key in ctx:
        if key in RESERVED_KEYS:
            err(f"`{key}` is a reserved identity key and cannot be set via --ctx")
            return None
        if not SLUG_RE.match(key):
            err(
                f"invalid context var name `{key}` — must be lowercase letters, "
                "digits, and underscores, not starting with a digit"
            )
            return None
    return ctx


def _print_tool_result(result: Any, pretty: bool) -> None:
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


@tool.command("call", aliases=["exec", "run"])
@click.argument("tool")
@click.argument("params", nargs=-1)
@click.option(
    "--json",
    "json_str",
    default=None,
    help="JSON object of parameters. Prefix with @ to read from a file "
    "(@params.json) or stdin (@-).",
)
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
    help="JSON object of context vars (merged with --ctx, --ctx wins on conflict). "
    "Prefix with @ to read from a file (@ctx.json) or stdin (@-).",
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

        mcc tool call my.tool --json @params.json

        mcc tool call public.request url=https://example.com --as ci-bot

        mcc tool call my.tool --ctx target_host=10.0.0.5 --ctx budget=100

        mcc tool call my.tool --json @- < params.json
    """

    t = loader.get(tool)
    if not t:
        err(f" tool `{tool}` not found in loaded tools: {','.join(loader)}")
        return

    current_user = _resolve_caller(as_user)
    if current_user is None:
        return

    kwargs = _build_kwargs(json_str, params)
    if kwargs is None:
        return

    ctx = _build_context_vars(ctx_json_str, ctx_vars)
    if ctx is None:
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
    except ValidationError as e:
        err(t.format_validation_error(e))
        return
    except Exception as e:  # noqa: BLE001
        err(e)
        return

    _print_tool_result(result, pretty)
