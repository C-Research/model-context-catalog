import asyncio
import json
import sys

import rich_click as click
from rich.console import Console
from rich.table import Table

from mcc.auth import (
    add_group,
    add_tool,
    create_user,
    delete_user,
    list_users,
    remove_group,
    remove_tool,
)

click.rich_click.USE_MARKDOWN = True

console = Console(markup=True)


@click.group()
def cli():
    """**MCC** — Model Context Catalog management CLI."""


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
        create_user(username, email, list(tools), list(groups))
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}", err=True)
        sys.exit(1)
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
    users = list_users()
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
            u["username"],
            u.get("email") or "[dim]—[/dim]",
            ", ".join(u.get("groups") or []),
            ", ".join(u.get("tools") or []),
        )

    console.print(table)


@user.command("remove")
@click.argument("username")
def user_remove(username):
    """Remove an existing user."""
    try:
        delete_user(username)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}", err=True)
        sys.exit(1)
    console.print(f"User **{username}** removed.")


@user.command("grant")
@click.argument("username")
@click.option("-g", "--group", "groups", multiple=True, help="Group to grant")
@click.option("-t", "--tool", "tools", multiple=True, help="Tool to grant")
def user_grant(username, groups, tools):
    """Grant groups and/or tools to a user."""
    if not groups and not tools:
        console.print(
            "[red]Error:[/red] at least one `--group` or `--tool` is required.",
            err=True,
        )
        sys.exit(1)
    try:
        for g in groups:
            add_group(username, g)
        for t in tools:
            add_tool(username, t)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}", err=True)
        sys.exit(1)
    console.print("Permissions updated.")


@user.command("revoke")
@click.argument("username")
@click.option("-g", "--group", "groups", multiple=True, help="Group to revoke")
@click.option("-t", "--tool", "tools", multiple=True, help="Tool to revoke")
def user_revoke(username, groups, tools):
    """Revoke groups and/or tools from a user."""
    if not groups and not tools:
        console.print(
            "[red]Error:[/red] at least one `--group` or `--tool` is required.",
            err=True,
        )
        sys.exit(1)
    try:
        for g in groups:
            remove_group(username, g)
        for t in tools:
            remove_tool(username, t)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}", err=True)
        sys.exit(1)
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
    from rich.markdown import Markdown

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
        console.print(f"[red]Error:[/red] tool `{tool}` not found", err=True)
        sys.exit(1)

    kwargs: dict = {}
    if json_str:
        try:
            kwargs.update(json.loads(json_str))
        except json.JSONDecodeError as e:
            console.print(f"[red]Error:[/red] invalid JSON — {e}", err=True)
            sys.exit(1)

    for p in params:
        if "=" not in p:
            console.print(
                f"[red]Error:[/red] expected `key=value`, got `{p}`", err=True
            )
            sys.exit(1)
        key, _, value = p.partition("=")
        kwargs[key] = value

    try:
        result = asyncio.run(t.call(**kwargs))
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}", err=True)
        sys.exit(1)

    if result is not None:
        if isinstance(result, (dict, list)):
            console.print_json(json.dumps(result, default=str))
        else:
            console.print(result)
