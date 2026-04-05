import sys
from asyncio import run as arun

import rich_click as click
from rich.console import Console

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


from mcc.cli.tools import tool  # noqa: E402
from mcc.cli.users import user  # noqa: E402
from mcc.cli.mcp import mcp_cmd  # noqa: E402, F401

cli.add_command(user)
cli.add_command(tool)
cli.add_command(mcp_cmd)
