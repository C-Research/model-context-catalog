import asyncio
import json
import sys

import click

from mcc.auth import (
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
@click.option("-u", "--username", required=True, help="GitHub username (login handle)")
@click.option("-e", "--email", default=None, help="User's email address (optional)")
@click.option("-g", "--group", "groups", multiple=True, help="Group to grant")
@click.option("-t", "--tool", "tools", multiple=True, help="Tool to grant")
def add_user_cmd(username, email, groups, tools):
    """Create a new user."""
    try:
        create_user(username, email, list(tools), list(groups))
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    msg = f"User '{username}' added"
    if email:
        msg += f" (email={email})"
    if groups:
        msg += f" groups={','.join(groups)}"
    if tools:
        msg += f" tools={','.join(tools)}"
    click.echo(msg)


@cli.command("list-users")
def list_users_cmd():
    """List all users."""
    for user in list_users():
        parts = [user["username"]]
        if user.get("email"):
            parts.append(f"email={user['email']}")
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


@cli.command("list-tools")
def list_tools_cmd():
    """List all registered tools."""
    from mcc.loader import loader

    click.echo(loader.list_all())


@cli.command()
@click.argument("tool_key")
@click.argument("params", nargs=-1)
@click.option("--json", "json_str", default=None, help="JSON object of parameters")
def call(tool_key, params, json_str):
    """Look up a tool by key and call it.

    Accepts parameters as key=value pairs and/or a --json blob.

    Examples:

        mcc call admin.list_users

        mcc call my.tool name=foo count=3

        mcc call my.tool --json '{"name": "foo", "count": 3}'
    """
    from mcc.loader import loader

    tool = loader.get(tool_key)
    if not tool:
        click.echo(f"Error: tool '{tool_key}' not found", err=True)
        sys.exit(1)

    kwargs: dict = {}
    if json_str:
        try:
            kwargs.update(json.loads(json_str))
        except json.JSONDecodeError as e:
            click.echo(f"Error: invalid JSON — {e}", err=True)
            sys.exit(1)

    for p in params:
        if "=" not in p:
            click.echo(f"Error: expected key=value, got '{p}'", err=True)
            sys.exit(1)
        key, _, value = p.partition("=")
        kwargs[key] = value

    try:
        result = asyncio.run(tool.call(**kwargs))
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if result is not None:
        if isinstance(result, (dict, list)):
            click.echo(json.dumps(result, indent=2, default=str))
        else:
            click.echo(result)


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
