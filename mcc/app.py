from contextlib import asynccontextmanager

from fastmcp import FastMCP

from pydantic import ValidationError

from mcc.auth import get_current_user
from mcc.auth.backend import get_auth
from mcc.loader import loader
from mcc.settings import settings, logger


@asynccontextmanager
async def lifespan(server):
    await loader.save()
    yield


mcp = FastMCP("model-context-catalog (mcc)", auth=get_auth(), lifespan=lifespan)
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
    results = await loader.search(query, group)
    accessible = [tool.signature for tool in results if tool.can_access(user)]
    if not accessible:
        return "No tools matched your query."
    return "\n\n".join(accessible)


@mcp.tool()
async def execute(name: str, params: dict | None = None):
    """Execute a tool from the catalog by name with the given parameters."""
    if name not in loader:
        return f"Unknown tool: {name}"
    tool = loader[name]
    user = await get_current_user()
    if not tool.can_access(user):
        return "Unauthorized"
    username = f"{user.username}<{user.email}>" if user else "anonymous"
    logger.info("%s Calling %s with %s", username, tool.key, params)
    try:
        return await tool.call(**params or {})
    except ValidationError as e:
        return f"Validation error for tool '{name}': {e}"


if __name__ == "__main__":
    mcp.run(transport="http")
