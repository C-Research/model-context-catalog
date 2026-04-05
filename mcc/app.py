from contextlib import asynccontextmanager
from typing import Optional

from fastmcp import FastMCP
from fastmcp.server.middleware.timing import TimingMiddleware
from pydantic import ValidationError

from mcc.auth.backend import get_auth
from mcc.loader import loader
from mcc.middleware import AuthMiddleware, LoggingMiddleware, current_user_var
from mcc.settings import settings, logger


@asynccontextmanager
async def lifespan(server):
    await loader.save()
    yield


mcp = FastMCP("model-context-catalog (mcc)", auth=get_auth(), lifespan=lifespan)
mcp.loader = loader  # type: ignore[attr-defined]
mcp.add_middleware(AuthMiddleware())
mcp.add_middleware(LoggingMiddleware())
mcp.add_middleware(TimingMiddleware(logger))


def banner():
    logger.info("Starting up...")
    for key, value in settings.as_dict().items():
        logger.debug("Setting %s=%s", key, value)
    for path in loader.paths:
        logger.info("Tools from: %s", path)
    for key, value in loader.items():
        logger.debug("Tool: %s", value.signature)


@mcp.tool()
async def search(query: str, min_score: Optional[float] = None) -> str:
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

    To narrow by group, include the group name in your query (e.g. "admin shell command").

    Examples:
      search("run a shell command") → finds admin.shell
      search("make an http request") → finds public.request
      search("shell", min_score=5.0) → only returns results scoring above 5.0
      search("zzz_nonexistent") → returns low-scoring noise; retry with min_score to confirm nothing matches

    Args:
      query: Natural language description of what you're looking for. Include group
             names in the query to narrow results (e.g. "admin tools", "public request").
      min_score: Optional minimum relevance score. Results below this threshold are
                 excluded. Observe scores from an initial search to pick a good value.
    """
    user = current_user_var.get(None)
    results = await loader.search(query, min_score)
    accessible = [
        f"[{score:.2f}]\n{tool.signature}"
        for tool, score in results
        if tool.allows(user)
    ]
    if not accessible:
        return "No tools matched your query. Try expanding your query or reducing min_score"
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
      params: Dict of parameter name → value. Omit or pass null for tools with no required parameters.
    """
    if name not in loader:
        return f"Unknown tool: {name}"
    tool = loader[name]
    user = current_user_var.get(None)
    if not tool.allows(user):
        return "Unauthorized"
    try:
        return await tool.call(**params or {})
    except ValidationError as e:
        return f"Validation error for tool '{name}': {e}"


# --- Resources ---


@mcp.resource("catalog://tools")
async def catalog_tools() -> str:
    """List all tools the current user can access."""
    user = current_user_var.get(None)
    accessible = [tool.signature for tool in loader.values() if tool.allows(user)]
    return "\n\n".join(accessible) if accessible else "No accessible tools."


@mcp.resource("catalog://tools/{key}")
async def catalog_tool_by_key(key: str) -> str:
    """Get a single tool's signature by key."""
    if key not in loader:
        return f"Tool '{key}' not found."
    tool = loader[key]
    user = current_user_var.get(None)
    if not tool.allows(user):
        return f"Tool '{key}' not found."
    return tool.signature


@mcp.resource("user://me")
async def user_me() -> dict:
    """Current user's identity, groups, and specific tool grants (not comprehensive list)."""
    user = current_user_var.get(None)
    if user is None:
        return {"username": "anonymous", "email": None, "groups": [], "tools": []}
    return {
        "username": user.username,
        "email": user.email,
        "groups": user.groups,
        "tools": user.tools,
    }


# --- Prompts ---


@mcp.prompt
def find_and_run(task: str) -> str:
    """Find a tool for a task and execute it."""
    return (
        f"Search the tool catalog for a tool that can: {task}. "
        "Review the results, pick the best match, and execute it with appropriate parameters."
    )


@mcp.prompt
def explain_tool(key: str) -> str:
    """Explain what a tool does, its parameters, and when to use it."""
    return (
        f"Read the tool catalog entry for '{key}' and explain:\n"
        "1. What the tool does\n"
        "2. What parameters it accepts (required vs optional)\n"
        "3. When you would use this tool"
    )


@mcp.prompt
def debug_error(key: str, error: str) -> str:
    """Diagnose a tool execution error and suggest fixes."""
    return (
        f"The tool '{key}' returned this error:\n\n{error}\n\n"
        "Diagnose what went wrong and suggest:\n"
        "1. How to fix the parameters or input\n"
        "2. Whether a different tool would be more appropriate\n"
        "3. Any other troubleshooting steps"
    )


if __name__ == "__main__":
    banner()
    mcp.run()
