"""Request-scoped user context and its propagation into tool subprocesses.

This module is intentionally dependency-free (stdlib + UserModel only) so it can
be imported by mcc.exec without creating an import cycle
(middleware -> auth -> models -> exec). middleware.py re-exports current_user_var
for backwards compatibility.

The caller's identity plus any mutable session vars live in a single context
dict ("one var to rule them all"). It is propagated to tool subprocesses two
ways:

- fn (Python) tools get the whole dict as one JSON env var, MCC_CTX, which
  pyrunner loads and may inject as a `context` kwarg.
- exec (shell) tools get each entry expanded into MCC_CTX_<NAME>, stringified.

`current_user_var` remains the single authoritative source of identity (set per
request by AuthMiddleware from the validated auth token). The identity fields in
any stored/assembled context are a re-derived snapshot — never trusted for RBAC.
"""

import json
import re
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcc.auth.models import UserModel

# Set per request by AuthMiddleware; read wherever the caller's identity is needed.
current_user_var: ContextVar = ContextVar("current_user", default=None)

# Set per execute() call to the assembled context dict (identity + stored vars)
# so the subprocess-spawning layer (mcc.exec) can build the right env without
# threading it through the tool-param kwargs. Defaults to None (no context).
current_context_var: ContextVar = ContextVar("current_context", default=None)

# Env var prefix for context entries expanded into exec subprocesses. Namespaced
# as MCC_CTX_* (not bare MCC_*) to stay out of the dynaconf settings namespace.
ENV_PREFIX = "MCC_CTX_"

# Single JSON-blob env var carrying the whole context dict to fn subprocesses.
ENV_BLOB = "MCC_CTX"

# Reserved keys always populated from the authenticated user. set_session refuses
# to write these so a tool/LLM cannot spoof identity.
RESERVED_KEYS = frozenset({"user", "email", "groups", "tools"})

# Valid context var name: lowercase, doubles as a JSON key, tool arg, and env
# suffix (uppercased) without sanitization collisions.
SLUG_RE = re.compile(r"^[a-z_][a-z0-9_]*$")

# Label used for the username component of the scope key when unauthenticated.
ANONYMOUS = "anonymous"

# A fn callable parameter with this name receives the assembled context dict
# (injected by pyrunner from MCC_CTX). It is shadowed from the LLM-facing schema.
CONTEXT_PARAM = "context"


def identity_fields(user: "UserModel | None") -> dict[str, Any]:
    """Build the reserved identity keys for the context dict from a UserModel.

    Anonymous (user is None) → only ``user="anonymous"``. For an authed user,
    email is included only when set; groups/tools are always present as lists
    (possibly empty) since their type is fixed.
    """
    if user is None:
        return {"user": ANONYMOUS}
    fields: dict[str, Any] = {"user": user.username}
    if user.email:
        fields["email"] = user.email
    fields["groups"] = list(user.groups)
    fields["tools"] = list(user.tools)
    return fields


def scope_username(user: "UserModel | None") -> str:
    """Username component of the (session, user) scope key."""
    return user.username if user is not None else ANONYMOUS


def state_key(user: "UserModel | None") -> str:
    """State key for the context blob. FastMCP further prefixes the session id,
    yielding ``{session_id}:{username}:context``."""
    return f"{scope_username(user)}:context"


def assemble_context(
    stored_vars: dict[str, Any] | None, user: "UserModel | None"
) -> dict[str, Any]:
    """Merge re-derived identity over the stored mutable vars (identity wins).

    The stored blob is treated as a read snapshot; its identity fields (if any)
    are always overwritten by fields freshly derived from `user`, so a stale or
    tampered blob can never impersonate or outlive a permission change.
    """
    merged: dict[str, Any] = dict(stored_vars or {})
    merged.update(identity_fields(user))
    return merged


def ctx_blob_env(context: dict[str, Any]) -> dict[str, str]:
    """fn tools: the whole context dict as one JSON env var (MCC_CTX)."""
    return {ENV_BLOB: json.dumps(context)}


def _stringify(value: Any) -> str:
    """Render a context value for an exec env var: scalars raw, complex JSON."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (str, int, float)):
        return str(value)
    return json.dumps(value)


def ctx_expanded_env(context: dict[str, Any]) -> dict[str, str]:
    """exec tools: each entry expanded into MCC_CTX_<NAME> (uppercased), with
    scalar values written raw and complex values (dict/list) JSON-encoded."""
    return {
        f"{ENV_PREFIX}{name.upper()}": _stringify(value)
        for name, value in context.items()
    }
