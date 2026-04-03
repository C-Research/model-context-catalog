from fastmcp import FastMCP
from pydantic import ValidationError

from .loader import loader

mcp = FastMCP("model-context-catalog")
mcp.loader = loader


@mcp.tool()
def search(query: str, group: str | None = None) -> str:
    """Search the tool catalog by name or description. Optionally filter by group."""
    query_lower = query.lower()
    results = []
    for name, entry in loader.items():
        if group is not None and entry.get("group") != group:
            continue
        if query_lower in name.lower() or query_lower in entry["description"].lower():
            parts = []
            for p in entry["parameters"]:
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
def execute(name: str, params: dict):
    """Execute a tool from the catalog by name with the given parameters."""
    if name not in loader:
        return f"Unknown tool: {name}"
    entry = loader[name]
    try:
        validated = entry["model"](**params)
    except ValidationError as e:
        return f"Validation error for tool '{name}': {e}"
    return entry["fn"](**validated.model_dump())
