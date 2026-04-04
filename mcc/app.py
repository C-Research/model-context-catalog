from fastmcp import FastMCP

from pydantic import ValidationError

from mcc.auth import get_current_user
from mcc.auth.backend import get_auth
from mcc.loader import loader
from mcc.settings import settings, logger


mcp = FastMCP("model-context-catalog", auth=get_auth())
mcp.loader = loader  # type: ignore[attr-defined]

logger.info("Starting up...")
for key, value in settings.as_dict().items():
    logger.debug("Setting %s=%s", key, value)
for path in loader.paths:
    logger.info("Tools from: %s", path)
for key, value in loader.items():
    logger.debug("Tool: %s", value.signature)


@mcp.tool()
async def search(query: str, group: str | None = None) -> str:
    """Search the tool catalog by name or description. Optionally filter by group."""
    user = await get_current_user()
    query_lower = query.lower()
    results = []
    for name, tool in loader.items():
        if not tool.can_access(user):
            continue
        if group is not None and tool.group != group:
            continue
        if query_lower in name.lower() or (
            tool.description and query_lower in tool.description.lower()
        ):
            results.append(tool.signature)
    if not results:
        return "No tools matched your query."
    return "\n\n".join(results)


@mcp.tool()
async def execute(name: str, params: dict | None = None):
    """Execute a tool from the catalog by name with the given parameters."""
    if name not in loader:
        return f"Unknown tool: {name}"
    tool = loader[name]
    user = await get_current_user()
    if not tool.can_access(user):
        return "Unauthorized"
    username = f"{user['username']}<{user.get('email')}>" if user else "anonymous"
    logger.info("%s Calling %s with %s", username, tool.key, params)
    try:
        return await tool.call(**params or {})
    except ValidationError as e:
        return f"Validation error for tool '{name}': {e}"


if __name__ == "__main__":
    mcp.run(transport="http")
