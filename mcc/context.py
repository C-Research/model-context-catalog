"""Request-scoped user identity/context and its propagation into tool subprocesses.

UserModel lives here (not in mcc.auth.models, where it used to live) because
mcc.exec and mcc.models need it and must stay import-cycle-free: mcc.auth's
package __init__ eagerly imports mcc.auth.db/util, which pulls in mcc.db,
which (via mcc.db.base -> mcc.models) would cycle straight back to whichever
module imported UserModel from inside the auth package. This module has no
such baggage -- stdlib + pydantic only -- so it's the safe common home.
middleware.py re-exports current_user_var for backwards compatibility.

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

from pydantic import BaseModel

if TYPE_CHECKING:
    from mcc.models import ToolModel


class UserModel(BaseModel):
    username: str
    email: str | None = None
    groups: list[str] = []
    tools: list[str] = []
    # Populated by list_users()'s batch enrichment ({"prefix", "created_at",
    # "expires_at"}) or, per-request, by get_current_user()/get_user_by_key()
    # when the caller authenticated via an API key ({"prefix"} only) — never
    # the hash or raw key. Never persisted — every write site (create_user,
    # _update_user) excludes it explicitly so a stale key snapshot never
    # round-trips into the users index.
    key: dict | None = None

    @property
    def is_anonymous(self) -> bool:
        """True only for the AnonymousUser sentinel. Overridden there;
        every resolved identity is False."""
        return False

    @property
    def is_admin(self) -> bool:
        """True if this user belongs to the admin group, which bypasses
        every other access check (see can_access, get_user_by_key)."""
        return "admin" in self.groups

    @property
    def accessible_tools(self) -> list["ToolModel"]:
        """Every tool this user can call: public tools, tools reachable via
        group membership, and tools granted directly via `self.tools`.

        Deferred import breaks the cycle loader.py -> mcc.models -> (this
        property) -> loader.py -- same reason ToolModel.allows() defers its
        `from mcc.auth import can_access` import in mcc/models.py.
        """
        from mcc.loader import loader

        return sorted(
            (tool for tool in loader.values() if tool.allows(self)), key=lambda t: t.key
        )


class AnonymousUser(UserModel):
    """Sentinel identity for unauthenticated callers, used everywhere a
    resolved user would otherwise be `None` -- so accessible_tools/is_admin/
    etc. work without a null check at every call site. Never persisted; the
    users index only ever stores real UserModel records."""

    username: str = "anonymous"

    @property
    def is_anonymous(self) -> bool:
        return True

    @property
    def is_admin(self) -> bool:
        return False


ANONYMOUS_USER = AnonymousUser()

# Set per request by AuthMiddleware; read wherever the caller's identity is needed.
# Defaults to ANONYMOUS_USER (never None) so every reader can call user.groups/
# user.accessible_tools/etc. without a null check.
current_user_var: ContextVar[UserModel] = ContextVar(
    "current_user", default=ANONYMOUS_USER
)

# Set per execute() call to the assembled context dict (identity + stored vars)
# so the subprocess-spawning layer (mcc.exec) can build the right env without
# threading it through the tool-param kwargs. Defaults to None (no context).
current_context_var: ContextVar = ContextVar("current_context", default=None)

# Sentinel distinguishing "an fn tool produced no write-back this call" (default)
# from "the tool returned an explicit context to write" (which may be {} = clear).
NO_WRITEBACK = object()

# Back-channel from mcc.exec (which unwraps the pyrunner [result, context] envelope
# but has no FastMCP Context) to app.execute (which owns ctx.set_state). Set per
# call to the returned context dict; app.execute reads it after the tool returns and
# applies the guarded write. Mirrors current_context_var in the opposite direction.
writeback_context_var: ContextVar = ContextVar(
    "writeback_context", default=NO_WRITEBACK
)

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


def identity_fields(user: UserModel) -> dict[str, Any]:
    """Build the reserved identity keys for the context dict from a UserModel.

    Anonymous (user.is_anonymous) → only ``user="anonymous"``. For a resolved
    identity, email is included only when set; groups/tools are always
    present as lists (possibly empty) since their type is fixed.
    """
    if user.is_anonymous:
        return {"user": ANONYMOUS}
    fields: dict[str, Any] = {"user": user.username}
    if user.email:
        fields["email"] = user.email
    fields["groups"] = list(user.groups)
    fields["tools"] = list(user.tools)
    return fields


def scope_username(user: UserModel) -> str:
    """Username component of the (session, user) scope key."""
    return ANONYMOUS if user.is_anonymous else user.username


def state_key(user: UserModel) -> str:
    """State key for the context blob. FastMCP further prefixes the session id,
    yielding ``{session_id}:{username}:context``."""
    return f"{scope_username(user)}:context"


def assemble_context(stored_vars: dict[str, Any] | None, user: UserModel) -> dict[str, Any]:
    """Merge re-derived identity over the stored mutable vars (identity wins).

    The stored blob is treated as a read snapshot; its identity fields (if any)
    are always overwritten by fields freshly derived from `user`, so a stale or
    tampered blob can never impersonate or outlive a permission change.
    """
    merged: dict[str, Any] = dict(stored_vars or {})
    merged.update(identity_fields(user))
    return merged


def sanitize_writeback(returned: dict[str, Any]) -> dict[str, Any] | None:
    """Validate an fn tool's returned context before it replaces session state.

    Applies the same guard as set_session, over all keys at once, and returns the
    bare non-identity vars to persist (identity is never stored — it is re-derived
    from the authenticated user on every read via assemble_context):
    - Reserved identity keys are stripped silently — they are injected into every
      context a tool receives, so their presence is expected, not an error. A tool
      cannot set, alter, or delete them: they are dropped here and re-derived on read.
    - Every remaining key must match SLUG_RE (it becomes MCC_CTX_<NAME> env for
      downstream tools). A single invalid key rejects the WHOLE write-back by raising
      ValueError(name), so the caller can log the offending key and skip the write,
      leaving stored state unchanged.

    Returns the stripped dict to store on success. Raises ValueError naming the first
    invalid key on reject.
    """
    stripped: dict[str, Any] = {}
    for name, value in returned.items():
        if name in RESERVED_KEYS:
            continue
        if not SLUG_RE.match(name):
            raise ValueError(name)
        stripped[name] = value
    return stripped


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
