from contextlib import asynccontextmanager
from typing import Optional

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
async def search(query: str, group: Optional[str] = None, min_score: Optional[float] = None) -> str:
    """Search the tool catalog using natural language. Combines keyword and semantic
    similarity for best results.

    Each result is prefixed with a relevance score in brackets, e.g. [8.42]. Scores
    are relative — compare them to each other, not to any fixed scale. A large gap
    between the top scores and the rest (e.g. 9.1, 8.7, 0.4, 0.3) means the
    lower-scored results are probably not relevant to your query.

    Use min_score to filter out low-confidence results. Start with an initial search
    to observe the score distribution, then retry with min_score set just above the
    gap to get a clean result set. Typical useful scores range from 1.0 to 15.0
    depending on query specificity.

    Each result includes the tool key, groups, parameters with types and descriptions,
    return type, and a description. Use the tool key with execute() to invoke a tool.

    Examples:
      search("run a shell command") → finds admin.shell
      search("make an http request") → finds public.request
      search("reload tools", group="admin") → finds admin.reload, filtered to admin group
      search("shell", min_score=5.0) → only returns results scoring above 5.0
      search("zzz_nonexistent") → returns low-scoring noise; retry with min_score to confirm nothing matches

    Args:
      query: Natural language description of what you're looking for.
      group: Optional group name to restrict results to tools in that group.
      min_score: Optional minimum relevance score. Results below this threshold are
                 excluded. Observe scores from an initial search to pick a good value.
    """
    user = await get_current_user()
    results = await loader.search(query, group, min_score)
    accessible = [
        f"[{score:.2f}]\n{tool.signature}"
        for tool, score in results
        if tool.can_access(user)
    ]
    if not accessible:
        return "No tools matched your query."
    return "\n\n".join(accessible)


@mcp.tool()
async def execute(name: str, params: Optional[dict] = None):
    """Execute a tool from the catalog by its exact key.

    The tool key is shown in search() results (e.g. "admin.shell", "public.request").
    Pass parameters as a dict matching the tool's declared parameter names and types.
    Required parameters must be included; optional parameters may be omitted.

    Examples:
      execute("admin.shell", {"command": "ls -la"})
      execute("public.request", {"url": "https://example.com"})
      execute("admin.reload")

    Args:
      name: Exact tool key from search results.
      params: Dict of parameter name → value. Omit or pass null for tools with no
              required parameters.
    """
    if name not in loader:
        return f"Unknown tool: {name}"
    tool = loader[name]
    user = await get_current_user()
    if not tool.can_access(user):
        return "Unauthorized"
    username = f"{user.username}<{user.email}>" if user else "anonymous"
    logger.info("%s calling %s with %s", username, tool.key, params)
    try:
        return await tool.call(**params or {})
    except ValidationError as e:
        return f"Validation error for tool '{name}': {e}"


if __name__ == "__main__":
    mcp.run(transport="http")
