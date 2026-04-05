from asyncio import run as arun
from pathlib import Path
from typing import Optional

import rich_click as click

from mcc.cli import cli

_SERVER_SPEC = "mcc/app.py:mcp"
_EDITABLE = Path(".")


@cli.group("mcp")
def mcp_cmd():
    """Runs methods for fastmcp"""


@mcp_cmd.command("serve")
@click.option(
    "-t",
    "--transport",
    type=click.Choice(["stdio", "http"]),
    default="stdio",
    show_default=True,
    help="Transport protocol.",
)
@click.option("-h", "--host", default="0.0.0.0", help="Host to bind (HTTP transports).")
@click.option(
    "-p", "--port", default=8000, type=int, help="Port to bind (HTTP transports)."
)
def run(transport: str, host: Optional[str], port: Optional[int]):
    """Start the MCP server."""
    from mcc.app import mcp

    kwargs = {"host": host, "port": port} if transport == "http" else {}
    mcp.run(transport=transport, **kwargs)


@mcp_cmd.group("install")
def install():
    """Install MCC in Claude clients."""


def common_options(fn):
    fn = click.option(
        "--env-file",
        default=None,
        type=click.Path(),
        help="Load env vars from a .env file.",
    )(fn)
    fn = click.option("--env", multiple=True, help="Env var in KEY=VALUE format.")(fn)
    return fn


def do_install(dest: str, **kwargs):
    from fastmcp.cli.cli import app

    arun(
        app["install"][dest].default_command(
            _SERVER_SPEC,
            server_name=app.name,
            with_editable=[_EDITABLE],
            env_vars=list(kwargs["env"]) or None,
            env_file=Path(kwargs["env_file"]) if kwargs["env_file"] else None,
        )
    )


@install.command("claude-code")
@common_options
def install_claude_code(env_file: Optional[str], env: tuple[str, ...]):
    """Install MCC in Claude Code."""
    do_install("claude-code", env=env, env_file=env_file)


@install.command("claude-desktop")
@common_options
def install_claude_desktop(env_file: Optional[str], env: tuple[str, ...]):
    """Install MCC in Claude Desktop."""
    do_install("claude-desktop", env=env, env_file=env_file)


@install.command("mcp-json")
@common_options
@click.option(
    "--copy", is_flag=True, default=False, help="Copy to clipboard instead of printing."
)
def install_mcp_json(env_file: Optional[str], env: tuple[str, ...], copy: bool):
    """Print (or copy) MCP JSON config."""
    do_install("mcp-json", env=env, env_file=env_file, copy=copy)
