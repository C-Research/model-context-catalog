import sys

import click

from .auth import (
    add_group,
    add_tool,
    create_user,
    delete_user,
    list_users,
    remove_group,
    remove_tool,
)


@click.group()
def cli():
    """MCC — Model Context Catalog management CLI."""


@cli.command("add-user")
@click.argument("username")
@click.option("-g", "--group", "groups", multiple=True, help="Group to grant")
@click.option("-t", "--tool", "tools", multiple=True, help="Tool to grant")
def add_user_cmd(username, groups, tools):
    """Create a new user and print their bearer token."""
    try:
        token = create_user(username, tools, groups)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    click.echo(
        f"User {username} added with tools={','.join(tools)} groups={','.join(groups)}"
    )
    click.echo(f"Token: {token}")
    click.echo("Save this token — it will not be shown again.", err=True)


@cli.command("list-users")
def list_users_cmd():
    """List all users."""
    for user in list_users():
        parts = [user["username"]]
        if user.get("groups"):
            parts.append(f"groups={','.join(user['groups'])}")
        if user.get("tools"):
            parts.append(f"tools={','.join(user['tools'])}")
        click.echo("  ".join(parts))


@cli.command("remove-user")
@click.argument("username")
def remove_user_cmd(username):
    """Remove an existing user."""
    try:
        delete_user(username)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    click.echo(f"User '{username}' removed.")


@cli.command()
@click.argument("username")
@click.option("-g", "--group", "groups", multiple=True, help="Group to grant")
@click.option("-t", "--tool", "tools", multiple=True, help="Tool to grant")
def grant(username, groups, tools):
    """Grant groups and/or tools to a user."""
    if not groups and not tools:
        click.echo("Error: at least one --group or --tool is required.", err=True)
        sys.exit(1)
    try:
        for g in groups:
            add_group(username, g)
        for t in tools:
            add_tool(username, t)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    click.echo("Permissions updated.")


@cli.command()
@click.argument("username")
@click.option("-g", "--group", "groups", multiple=True, help="Group to revoke")
@click.option("-t", "--tool", "tools", multiple=True, help="Tool to revoke")
def revoke(username, groups, tools):
    """Revoke groups and/or tools from a user."""
    if not groups and not tools:
        click.echo("Error: at least one --group or --tool is required.", err=True)
        sys.exit(1)
    try:
        for g in groups:
            remove_group(username, g)
        for t in tools:
            remove_tool(username, t)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    click.echo("Permissions updated.")
