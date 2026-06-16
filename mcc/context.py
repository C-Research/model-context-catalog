"""Request-scoped user context and its propagation into tool subprocesses.

This module is intentionally dependency-free (stdlib + UserModel only) so it can
be imported by mcc.exec without creating an import cycle
(middleware -> auth -> models -> exec). middleware.py re-exports current_user_var
for backwards compatibility.
"""

from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcc.auth.models import UserModel

# Set per request by AuthMiddleware; read wherever the caller's identity is needed.
current_user_var: ContextVar = ContextVar("current_user", default=None)

# Env var prefix for identity propagated into tool subprocesses. Namespaced as
# MCC_CTX_* (not bare MCC_*) to stay out of the dynaconf settings namespace.
ENV_PREFIX = "MCC_CTX_"


def user_env(user: "UserModel | None") -> dict[str, str]:
    """Build the MCC_CTX_* env vars carrying the caller's identity to a subprocess.

    Lists are comma-joined (group/tool keys never contain commas). A field is
    omitted entirely when empty so a tool can distinguish "absent" (anonymous /
    no email / no groups) from an empty value. Returns {} for an anonymous request.

    MCC_CTX_TOOLS carries the user's *direct* tool grants; indirect access is
    derivable from MCC_CTX_GROUPS.
    """
    if user is None:
        return {}
    env = {f"{ENV_PREFIX}USER": user.username}
    if user.email:
        env[f"{ENV_PREFIX}EMAIL"] = user.email
    if user.groups:
        env[f"{ENV_PREFIX}GROUPS"] = ",".join(user.groups)
    if user.tools:
        env[f"{ENV_PREFIX}TOOLS"] = ",".join(user.tools)
    return env
