import sys
from asyncio import run as arun

import rich_click as click
from rich.console import Console

from mcc.loader import loader
from mcc.settings import logger, settings

click.rich_click.USE_MARKDOWN = True
click.rich_click.USE_RICH_MARKUP = True

console = Console(markup=True)


def err(msg, exit=1):
    console.print(f"[red]Error: {msg}[/red]", markup=True)
    sys.exit(exit)


@click.group()
@click.option("-t", "--tool", multiple=True, help="Tool files to load on startup")
@click.option(
    "-e",
    "--env",
    default=None,
    help="Dynaconf environment to use eg development/production",
)
@click.option(
    "-v", "--verbose", is_flag=True, default=False, help="Enable debug logging."
)
def cli(tool, env, verbose):
    """**MCC** — Model Context Catalog management CLI."""
    logger.setLevel("DEBUG" if verbose else "INFO")
    try:
        arun(loader.save())
    except Exception as exc:
        err(f"ES Connection error: {exc}")
    if env is not None:
        settings.setenv(env)
    loader.load(*tool)


from mcc.cli.mcp import mcp_cmd  # noqa: E402, F401
from mcc.cli.tools import tool  # noqa: E402
from mcc.cli.users import user  # noqa: E402

cli.add_command(user)
cli.add_command(tool)
cli.add_command(mcp_cmd)
