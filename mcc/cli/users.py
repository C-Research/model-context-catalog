from asyncio import run as arun

import rich_click as click

from mcc.auth import (
    add_group,
    add_tool,
    create_user,
    delete_user,
    list_users,
    remove_group,
    remove_tool,
)

from mcc.cli import console, err


@click.group()
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
    from rich.table import Table

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
