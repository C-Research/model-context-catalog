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
    from mcc.app import mcp, banner

    banner()
    kwargs = {"host": host, "port": port} if transport == "http" else {}
    mcp.run(transport=transport, **kwargs)  # type: ignore[arg-type]  # click.Choice doesn't narrow to Literal


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
    import inspect
    from fastmcp.cli.cli import app

    install_cmd = app["install"][dest].default_command
    assert install_cmd is not None, f"No default_command for install target '{dest}'"

    supported = inspect.signature(install_cmd).parameters
    call_kwargs: dict = {
        "server_name": app.name,
        "with_editable": [_EDITABLE],
    }
    if "env_vars" in supported:
        call_kwargs["env_vars"] = list(kwargs["env"]) or None
    if "env_file" in supported:
        call_kwargs["env_file"] = (
            Path(kwargs["env_file"]) if kwargs["env_file"] else None
        )
    if "copy" in supported and "copy" in kwargs:
        call_kwargs["copy"] = kwargs["copy"]

    arun(install_cmd(_SERVER_SPEC, **call_kwargs))


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


@install.command("cursor")
@common_options
def install_cursor(env_file: Optional[str], env: tuple[str, ...]):
    """Install MCC in Cursor."""
    do_install("cursor", env=env, env_file=env_file)


@install.command("gemini-cli")
@common_options
def install_gemini_cli(env_file: Optional[str], env: tuple[str, ...]):
    """Install MCC in Gemini CLI."""
    do_install("gemini-cli", env=env, env_file=env_file)


@install.command("goose")
@common_options
def install_goose(env_file: Optional[str], env: tuple[str, ...]):
    """Install MCC in Goose."""
    do_install("goose", env=env, env_file=env_file)
