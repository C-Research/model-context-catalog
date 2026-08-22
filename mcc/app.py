import json
from contextlib import asynccontextmanager
from typing import Optional

from fastmcp import Context, FastMCP
from mcp.types import Icon
from fastmcp.server.elicitation import (
    AcceptedElicitation,
    CancelledElicitation,
    DeclinedElicitation,
)
from fastmcp.server.event_store import EventStore
from fastmcp.server.middleware.response_limiting import ResponseLimitingMiddleware
from fastmcp.server.middleware.timing import TimingMiddleware
from pydantic import Field, ValidationError, create_model

from mcc import __version__
from mcc.auth import whoami_info
from mcc.auth.backend import get_provider
from mcc.cache import cached, params_hash
from mcc.context import (
    NO_WRITEBACK,
    RESERVED_KEYS,
    SLUG_RE,
    assemble_context,
    current_context_var,
    current_user_var,
    sanitize_writeback,
    state_key,
    writeback_context_var,
)
from mcc.db import session_store
from mcc.loader import loader
from mcc.middleware import AuthMiddleware, LoggingMiddleware, RateLimitMiddleware
from mcc.routes import register_routes
from mcc.settings import logger, settings


@asynccontextmanager
async def lifespan(server):
    await loader.save()
    yield


# Session-scoped context store. Both backends derive index names as
# "{index_prefix}-{collection}", and FastMCP's state store uses the collection
# "fastmcp_state", so this touches only "mcc-ctx-fastmcp_state" and cannot clobber
# the users/tools/keys indices. session_store() picks the backend matching
# settings.SEARCH_BACKEND, so this needs no Elasticsearch cluster reachable
# when running OpenSearch. Default 24h TTL is FastMCP's and needs no setting.
_session_store = session_store("mcc-ctx")

# Event store for streamable-http stream resumability (Mcp-Session-Id +
# Last-Event-ID replay after a dropped connection). Backend is a URI, same
# convention as cache.backend. "mem://" (default) keeps replay state
# in-process, so a reconnect that lands on a different pod can never resume;
# "redis://..." survives pod restarts. redis is only imported when that
# backend is chosen, so mcc has no hard redis dependency.
_event_store_backend = settings.get("event_store", {}).get("backend", "mem://")
if _event_store_backend.startswith(("redis://", "rediss://")):
    from key_value.aio.stores.redis import RedisStore

    event_store = EventStore(storage=RedisStore(url=_event_store_backend))
else:
    event_store = None

# Overrides the name/link/icon shown on the OAuth consent screen; see
# settings.yaml's `branding` block. Falls through to FastMCP's own defaults
# (server name, no link, no icon) when unset.
_branding = settings.get("branding") or {}

mcp = FastMCP(
    _branding.get("name") or "model-context-catalog (mcc)",
    version=__version__,
    auth=get_provider(),
    lifespan=lifespan,
    session_state_store=_session_store,
    website_url=_branding.get("website_url") or None,
    icons=[Icon(src=_branding["icon_url"])] if _branding.get("icon_url") else None,
)
mcp.loader = loader  # type: ignore[attr-defined]
mcp.add_middleware(AuthMiddleware())
mcp.add_middleware(LoggingMiddleware())
mcp.add_middleware(TimingMiddleware(logger))
mcp.add_middleware(
    ResponseLimitingMiddleware(max_size=settings.server.response_max_size)
)
if settings.get("rate_limit", {}).get("enabled", False):
    mcp.add_middleware(RateLimitMiddleware())

register_routes(mcp)


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


_ELICITABLE = {"str", "int", "float", "bool"}


class _ElicitationCancelled(Exception):
    """Raised when the caller declines or cancels elicitation of required params."""


async def _elicit_missing(ctx: Context, key: str, tool, params: Optional[dict]) -> dict:
    """Prompt the caller for any required, elicitable params not already supplied.

    Returns the params dict to call the tool with (the originals merged with any
    elicited values). Raises _ElicitationCancelled if the caller declines. If the
    elicitation itself fails, logs and returns the originals unchanged so the
    tool's own validation can surface the missing-param error.
    """
    missing = [
        p
        for p in tool.visible_params
        if p.required and p.name not in (params or {}) and p.type in _ELICITABLE
    ]
    if not missing:
        return params or {}
    fields: dict = {
        p.name: (p.py_type, Field(..., description=p.description)) for p in missing
    }
    MissingModel = create_model("MissingParams", **fields)
    summary = ", ".join(f"{p.name} ({p.type})" for p in missing)
    try:
        result = await ctx.elicit(f"Tool '{key}' requires: {summary}", MissingModel)
    except Exception as exc:
        logger.warning("elicitation failed for %s: %s", key, exc)
        return params or {}
    if isinstance(result, AcceptedElicitation):
        return {**(params or {}), **result.data.model_dump()}
    if isinstance(result, (DeclinedElicitation, CancelledElicitation)):
        raise _ElicitationCancelled
    return params or {}


def _coerce_result(result):
    """fn tools return JSON-encoded strings via subprocess; parse for natural values."""
    if isinstance(result, str):
        try:
            return json.loads(result)
        except (json.JSONDecodeError, ValueError):
            return result
    return result


async def _apply_writeback(ctx: Context, user) -> None:
    """Persist an fn tool's returned context into session state (full replace).

    Reads the context stashed on writeback_context_var by mcc.exec while unwrapping
    the pyrunner envelope. NO_WRITEBACK (no fn write-back this call) is a no-op. The
    returned dict is validated like set_session (reserved keys stripped and
    re-derived, remaining keys slug-checked); an invalid key rejects the whole
    write-back — the offending key is logged and the write skipped, never failing the
    already-completed tool call.
    """
    returned = writeback_context_var.get()
    if returned is NO_WRITEBACK:
        return
    try:
        sanitized = sanitize_writeback(returned)
    except ValueError as e:
        bad_key = e.args[0]
        logger.warning(
            "execute: rejected context write-back for %s — invalid key %r "
            "(must match %s); no session vars written",
            user.username if user else "anonymous",
            bad_key,
            SLUG_RE.pattern,
        )
        return
    await ctx.set_state(state_key(user), sanitized)


@mcp.tool()
async def execute(ctx: Context, key: str, params: Optional[dict] = None):
    """Execute a tool from the catalog by its exact key.

    The tool key is shown in search() results (e.g. "admin.shell", "public.request").
    Pass parameters as a dict matching the tool's declared parameter names and types.
    Required parameters must be included; optional parameters may be omitted.
    LLMs should not try to execute arbitrary tools by name as they might not exist.
    Instead use search first

    Examples:
      execute("admin.shell", {"command": "ls -la"})
      execute("public.request", {"url": "https://example.com"})
      execute("admin.reload")

    Args:
      key: Exact tool key from search results.
      params: Dict of parameter name → value. Omit or pass null for tools with no required parameters.
    """
    if key not in loader:
        logger.warning("execute: unknown tool %r", key)
        return f"Unknown tool: {key}"
    tool = loader[key]
    user = current_user_var.get(None)
    if not tool.allows(user):
        username = user.username if user else "anonymous"
        logger.warning("execute: %s denied access to %s", username, key)
        return "Unauthorized"
    # Assemble the caller's context snapshot once (stored session vars + identity
    # re-derived from current_user_var, identity wins) and expose it to the
    # subprocess-spawning layer for the duration of the call.
    stored = await ctx.get_state(state_key(user))
    context = assemble_context(stored, user)

    # Incorporate both the runtime params and the session context values into the cache key
    cache_key = (
        f"exec:{tool.key}:{params_hash(params)}:{params_hash(context)}"
        if tool.cache_ttl
        else None
    )

    async def _compute():
        # Elicitation is gated behind the cache lookup (it runs only on a miss),
        # so a cached result never re-prompts the caller.
        merged = await _elicit_missing(ctx, key, tool, params)
        token = current_context_var.set(context)
        wb_token = writeback_context_var.set(NO_WRITEBACK)
        try:
            result = _coerce_result(await tool.call(**merged))
            # fn-tool context write-back: exec.py stashes the tool's returned context
            # here. Runs only on a cache miss (inside _compute), so a cache hit never
            # re-writes state. Guarded exactly like set_session before persisting.
            await _apply_writeback(ctx, user)
            return result
        finally:
            writeback_context_var.reset(wb_token)
            current_context_var.reset(token)

    try:
        return await cached(cache_key, _compute, tool.cache_ttl)
    except _ElicitationCancelled:
        return "Execution cancelled: required parameters not provided"
    except ValidationError as e:
        return f"Validation error for tool '{key}': {e}"


@mcp.tool()
async def whoami() -> str:
    """Return the identity of the currently authenticated user.

    Resolves the caller's auth session (validated in this process — no token or
    secret is ever returned) to their catalog identity: username, email, the
    groups they belong to, and the tools they can execute.

    Use this to confirm who you are authenticated as and which groups/tools
    gate your access before searching or executing tools.
    Groups are the groups the user is in; membership grants access to every tool
    in those groups.
    Tools is the exhaustive list of tool keys the user can execute — the union of
    tools granted directly and all tools reachable through their group memberships.

    Returns a human-readable summary, or a notice if the request is unauthenticated.
    """
    user = current_user_var.get(None)
    if user is None:
        return "Not authenticated: no user is associated with this session."

    # Cache keyed on username. Invalidated on loader.reload() (the accessible-tool
    # set depends on the catalog) and on any modification to the user (mcc.auth.db).
    # Reuses search_ttl since both cache catalog-derived results.
    search_ttl = (settings.get("cache") or {}).get("search_ttl", 0)
    cache_key = f"whoami:{user.username}" if search_ttl else None

    async def _summary() -> str:
        info = whoami_info(user)
        lines = [
            f"username: {info['username']}",
            f"email: {info['email'] or '(none)'}",
            f"groups: {', '.join(info['groups']) if info['groups'] else '(none)'}",
            f"tools: {', '.join(info['tools']) if info['tools'] else '(none)'}",
        ]
        return "\n".join(lines)

    return await cached(cache_key, _summary, search_ttl)


@mcp.tool()
async def describe_tools(groups: Optional[list[str]] = None) -> str:
    """List all tools accessible to the current user with their descriptions.

    Use this only if everything else fails, returns many tools and will pollute context

    Returns tool keys and descriptions only — use search() to get full parameter
    details before calling execute().

    Args:
      groups: If provided, only return tools that belong to ALL of the specified groups.
    Example:
      describe_tools([admin,web])
    """
    user = current_user_var.get(None)
    tools = [t for t in loader.values() if t.allows(user)]
    if groups:
        groups_set = set(groups)
        tools = [t for t in tools if groups_set.issubset(set(t.groups))]
    if not tools:
        return "No tools available."
    return "\n\n".join(
        f"## {t.key}\n{t.description or ''}" for t in sorted(tools, key=lambda t: t.key)
    )


@mcp.tool()
async def set_session(ctx: Context, name: str, value: object) -> str:
    """Store a value in your session store for later tool calls to read.

    The session store is a per-session, per-user key/value bag. Anything you set
    here is visible to subsequent tool executions in this same session (Python tools
    can receive it as a `context` argument; shell tools see it as MCC_CTX_<NAME> env
    vars) without you having to re-pass it on every call. Use it to stash a value
    once — a target host, a budget, a selected record — and reuse it.

    `value` may be any JSON type (string, number, bool, list, object) and is stored
    with its type preserved.

    `name` must match ^[a-z_][a-z0-9_]*$ (lowercase letters, digits, underscores;
    not starting with a digit). The reserved identity keys (user, email, groups,
    tools) cannot be set — they always reflect the authenticated caller.

    Args:
      name: The variable name (slug). Lowercase letters/digits/underscores.
      value: Any JSON-serializable value to store.
    """
    if not SLUG_RE.match(name):
        return (
            f"Invalid name {name!r}: must match ^[a-z_][a-z0-9_]*$ "
            "(lowercase letters, digits, underscores; not starting with a digit)."
        )
    if name in RESERVED_KEYS:
        return f"Cannot set reserved identity key {name!r}."
    user = current_user_var.get(None)
    skey = state_key(user)
    stored = await ctx.get_state(skey) or {}
    stored[name] = value
    await ctx.set_state(skey, stored)
    return f"Set {name!r}."


@mcp.tool()
async def get_session(ctx: Context, name: str) -> str:
    """Read a value previously stored in your session store.

    Returns the value set by a prior `set_session(name, ...)` in this session as
    a JSON string, preserving its type: a string is quoted ("10.0.0.5"), a number
    is bare (1000), and lists/objects are JSON. The reserved identity keys (user,
    email, groups, tools) resolve to the authenticated caller's identity. Returns
    the JSON literal null when the name was never set.

    Args:
      name: The variable name to read.
    """
    user = current_user_var.get(None)
    stored = await ctx.get_state(state_key(user))
    context = assemble_context(stored, user)
    return json.dumps(context.get(name))


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
