import sys
from asyncio import run as arun

import rich_click as click
from rich.console import Console
from rich.errors import MarkupError

from mcc import __version__
from mcc.loader import loader
from mcc.settings import logger, settings

click.rich_click.USE_MARKDOWN = True
click.rich_click.USE_RICH_MARKUP = True

console = Console(markup=True)


def err(msg, exit=1):
    try:
        console.print(f"[red]Error: {msg}[/red]", markup=True)
    except MarkupError:
        # msg contained brackets that aren't valid markup (e.g. ES error
        # payloads like "[/]"); fall back to literal text with a red style.
        console.print(f"Error: {msg}", style="red", markup=False)
    sys.exit(exit)


@click.group()
@click.version_option(__version__, "-V", "--version", prog_name="mcc")
@click.option(
    "-e",
    "--env",
    default=None,
    help="Dynaconf environment to use eg development/production",
)
@click.option(
    "-v", "--verbose", is_flag=True, default=False, help="Enable debug logging."
)
@click.pass_context
def cli(ctx, env, verbose):
    """
    **MCC** — Model Context Catalog management CLI.

    Manage users, browse tools, and run the MCP server. Tool files and settings
    are configured via environment variables since they must be resolved before
    the CLI starts.

    ## Environment Variables

    - **MCC_TOOL_FILES** — Semicolon-separated paths to tool YAML files/directories to load on startup.

    - **MCC_SETTINGS_FILES** — Semicolon-separated paths to additional settings YAML files (merged after defaults).

    - **MCC_SKIP_AUTOLOAD** — Set to skip automatic tool loading at startup.
    """
    logger.setLevel("DEBUG" if verbose else "INFO")
    if ctx.invoked_subcommand != "download":
        try:
            arun(loader.save())
        except Exception as exc:  # noqa: BLE001
            err(f"ES Connection error: {exc}")
    if env is not None:
        settings.setenv(env)


from mcc.cli.audit import audit
from mcc.cli.download import download
from mcc.cli.mcp import mcp_cmd
from mcc.cli.tools import tool
from mcc.cli.users import user

cli.add_command(download)
cli.add_command(user)
cli.add_command(tool)
cli.add_command(mcp_cmd)
cli.add_command(audit)
