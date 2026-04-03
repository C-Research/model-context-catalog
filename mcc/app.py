import os

from fastmcp import Context, FastMCP
from fastmcp.server.auth.providers.github import GitHubProvider
from pydantic import ValidationError

from .auth import can_access, get_current_user
from .loader import loader


def _github_provider() -> GitHubProvider:
    client_id = os.environ.get("MCC_GITHUB_CLIENT_ID")
    client_secret = os.environ.get("MCC_GITHUB_CLIENT_SECRET")
    base_url = os.environ.get("MCC_BASE_URL")
    missing = [
        k
        for k, v in {
            "MCC_GITHUB_CLIENT_ID": client_id,
            "MCC_GITHUB_CLIENT_SECRET": client_secret,
            "MCC_BASE_URL": base_url,
        }.items()
        if not v
    ]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}"
        )
    return GitHubProvider(
        client_id=client_id,
        client_secret=client_secret,
        base_url=base_url,
    )


mcp = FastMCP("model-context-catalog", auth=_github_provider())
mcp.loader = loader


@mcp.tool()
async def search(
    query: str, group: str | None = None, ctx: Context | None = None
) -> str:
    """Search the tool catalog by name or description. Optionally filter by group."""
    user = await get_current_user(ctx)
    query_lower = query.lower()
    results = []
    for name, entry in loader.items():
        if not can_access(user, name, entry.get("group")):
            continue
        if group is not None and entry.get("group") != group:
            continue
        if query_lower in name.lower() or query_lower in entry["description"].lower():
            parts = []
            for p in entry["params"]:
                type_str = p.get("type", "str")
                if p.get("required", False):
                    parts.append(f"{p['name']}: {type_str}")
                else:
                    parts.append(f"{p['name']}?: {type_str} = {p.get('default')}")
            sig = ", ".join(parts)
            results.append(
                f'{name} — {entry["description"]}\n  execute("{name}", {{{sig}}})'
            )
    if not results:
        return "No tools matched your query."
    return "\n\n".join(results)


@mcp.tool()
async def execute(name: str, params: dict | None = None, ctx: Context | None = None):
    """Execute a tool from the catalog by name with the given parameters."""
    if name not in loader:
        return f"Unknown tool: {name}"
    entry = loader[name]
    user = await get_current_user(ctx)
    if not can_access(user, name, entry.get("group")):
        return "Unauthorized"
    try:
        validated = entry["model"](**params or {})
    except ValidationError as e:
        return f"Validation error for tool '{name}': {e}"
    return entry["fn"](**validated.model_dump())
