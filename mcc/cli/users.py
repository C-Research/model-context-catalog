from asyncio import run as arun

import rich_click as click

from mcc.auth import (
    add_group,
    add_tool,
    create_user,
    delete_user,
    get_user_by_username,
    list_users,
    remove_group,
    remove_tool,
)
from mcc.auth.keys import create_key, list_keys, revoke_key
from mcc.cli import console, err
from mcc.settings import settings


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


@user.group("key")
def key():
    """Manage a user's API key (one key per user)."""


@key.command("add")
@click.argument("username")
@click.option(
    "--expires",
    default=None,
    help="Days until the key expires, or 'never'. Defaults to the configured TTL.",
)
def key_add(username, expires):
    """Mint an API key for a user, replacing any existing key."""
    user = arun(get_user_by_username(username))
    if user is None:
        err(f"User '{username}' not found")
    ttl_days: int | None
    if expires is None:
        ttl_days = settings.API_KEY.default_ttl_days
    elif expires.lower() == "never":
        ttl_days = None
    elif expires.isdigit() and int(expires) > 0:
        ttl_days = int(expires)
    else:
        err(f"Invalid --expires value '{expires}': use a positive day count or 'never'")
        return
    raw_key = arun(create_key(username, ttl_days))
    expiry_note = "never expires" if ttl_days is None else f"expires in {ttl_days} days"
    console.print(f"API key for **{username}** ({expiry_note}):")
    console.print(f"\n    [bold]{raw_key}[/bold]\n")
    console.print(
        "[yellow]Copy it now — it is shown only once and cannot be recovered.[/yellow]"
    )


@key.command("list")
def key_list():
    """List API keys (prefix and timestamps only — never secrets)."""
    from rich.table import Table

    keys = arun(list_keys())
    if not keys:
        console.print("[dim]No keys found.[/dim]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("User")
    table.add_column("Prefix")
    table.add_column("Created")
    table.add_column("Expires")

    for k in keys:
        table.add_row(
            k["username"],
            f"mcc_{k['prefix']}",
            k.get("created_at") or "[dim]—[/dim]",
            k.get("expires_at") or "[dim]never[/dim]",
        )

    console.print(table)


@key.command("revoke")
@click.argument("username")
def key_revoke(username):
    """Revoke (delete) a user's API key."""
    try:
        arun(revoke_key(username))
    except ValueError as e:
        err(e)
    console.print(f"API key for **{username}** revoked.")
