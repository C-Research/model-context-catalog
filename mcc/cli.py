import asyncio
import json
import sys
from asyncio import run as arun

import rich_click as click
from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown

from mcc.auth import (
    add_group,
    add_tool,
    create_user,
    delete_user,
    list_users,
    remove_group,
    remove_tool,
)
from mcc.loader import loader

click.rich_click.USE_MARKDOWN = True
click.rich_click.USE_RICH_MARKUP = True

console = Console(markup=True)


def err(msg):
    console.print(f"[red]Error: {msg}[/red]", markup=True)
    sys.exit(1)


@click.group()
def cli():
    """**MCC** — Model Context Catalog management CLI."""
    arun(loader.save())


# ---------------------------------------------------------------------------
# user group
# ---------------------------------------------------------------------------


@cli.group()
def user():
    """Manage users and their permissions."""


@user.command("add")
@click.option("-u", "--username", required=True, help="GitHub username (login handle)")
@click.option("-e", "--email", default=None, help="User's email address")
@click.option("-g", "--group", "groups", multiple=True, help="Group to grant")
@click.option("-t", "--tool", "tools", multiple=True, help="Tool to grant")
def user_add(username, email, groups, tools):
    """Create a new user."""
    try:
        arun(create_user(username, email, list(tools), list(groups)))
    except ValueError as e:
        err(e)
    msg = f"User **{username}** added"
    if email:
        msg += f" `{email}`"
    if groups:
        msg += f" groups: {', '.join(f'`{g}`' for g in groups)}"
    if tools:
        msg += f" tools: {', '.join(f'`{t}`' for t in tools)}"
    console.print(msg)


@user.command("list")
def user_list():
    """List all users."""
    users = arun(list_users())
    if not users:
        console.print("[dim]No users found.[/dim]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("User")
    table.add_column("Email")
    table.add_column("Groups")
    table.add_column("Tools")

    for u in users:
        table.add_row(
            u.username,
            u.email or "[dim]—[/dim]",
            ", ".join(u.groups),
            ", ".join(u.tools),
        )

    console.print(table)


@user.command("remove")
@click.argument("username")
def user_remove(username):
    """Remove an existing user."""
    try:
        arun(delete_user(username))
    except ValueError as e:
        err(e)
    console.print(f"User **{username}** removed.")


@user.command("grant")
@click.argument("username")
@click.option("-g", "--group", "groups", multiple=True, help="Group to grant")
@click.option("-t", "--tool", "tools", multiple=True, help="Tool to grant")
def user_grant(username, groups, tools):
    """Grant groups and/or tools to a user."""
    if not groups and not tools:
        err("at least one `--group` or `--tool` is required.")
    try:
        for g in groups:
            arun(add_group(username, g))
        for t in tools:
            arun(add_tool(username, t))
    except ValueError as e:
        err(e)
    console.print("Permissions updated.")


@user.command("revoke")
@click.argument("username")
@click.option("-g", "--group", "groups", multiple=True, help="Group to revoke")
@click.option("-t", "--tool", "tools", multiple=True, help="Tool to revoke")
def user_revoke(username, groups, tools):
    """Revoke groups and/or tools from a user."""
    if not groups and not tools:
        err("at least one `--group` or `--tool` is required.")
    try:
        for g in groups:
            arun(remove_group(username, g))
        for t in tools:
            arun(remove_tool(username, t))
    except ValueError as e:
        err(e)
    console.print("Permissions updated.")


# ---------------------------------------------------------------------------
# tool group
# ---------------------------------------------------------------------------


@cli.group()
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

    console.print(Markdown(md))


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
