from mcc.auth.backend import get_user_context
from mcc.auth.db import get_user_by_email, get_user_by_username
from mcc.auth.keys import verify_api_key
from mcc.context import UserModel
from mcc.db import KeysIndex
from mcc.models import ToolModel
from mcc.settings import logger, settings


def validate_claims_settings() -> None:
    """Fails fast at startup if claims-based groups are enabled with an empty
    role_group_prefix, which would turn every role in the IdP into a group."""
    if settings.claims.roles_claim and not settings.claims.role_group_prefix:
        raise ValueError(
            "claims.role_group_prefix must be non-empty when claims.roles_claim is set"
        )


def groups_from_claims(claims: dict) -> list[str]:
    """MCC groups derived from the token's roles claim.

    Reads the exact key `claims.roles_claim` (IdP claim keys can be URLs full of
    dots and slashes, so no path traversal), keeps string roles starting with
    `claims.role_group_prefix` (case-sensitive), and strips the prefix. A bare
    prefix, non-string items, and a missing or non-list claim yield nothing.
    """
    roles_claim = settings.claims.roles_claim
    if not roles_claim:
        logger.debug("claim groups disabled: claims.roles_claim is not set")
        return []
    roles = claims.get(roles_claim)
    if roles is None:
        # Listing the keys that *are* present makes a wrong/misspelled roles_claim
        # (e.g. a namespace mismatch) obvious.
        logger.debug(
            "roles claim %r not in token; claim keys present: %s",
            roles_claim,
            sorted(claims),
        )
        return []
    if not isinstance(roles, list):
        logger.warning(
            "claim %r is not a list of roles (got %s); ignoring",
            roles_claim,
            type(roles).__name__,
        )
        return []
    prefix = settings.claims.role_group_prefix
    groups: list[str] = []
    ignored: list = []
    for role in roles:
        if not isinstance(role, str) or not role.startswith(prefix):
            ignored.append(role)
            continue
        group = role[len(prefix) :]
        if group and group not in groups:
            groups.append(group)
    logger.debug(
        "roles claim %r: roles=%s prefix=%r -> groups=%s (ignored: %s)",
        roles_claim,
        roles,
        prefix,
        groups,
        ignored,
    )
    return groups


def _verified_claim_groups(claims: dict) -> list[str]:
    """Claim-derived groups, discarded unless the email is verified (when required)."""
    groups = groups_from_claims(claims)
    require_verified = settings.claims.require_email_verified
    verified = claims.get("email_verified")
    logger.debug(
        "email_verified=%r require_email_verified=%s candidate groups=%s",
        verified,
        require_verified,
        groups,
    )
    if groups and require_verified and verified is not True:
        logger.warning(
            "ignoring roles for %s: email_verified is not true", claims.get("email")
        )
        return []
    return groups


def _group_matches(pattern: str, groups: list[str]) -> bool:
    """True if `pattern` grants access given a tool's authored groups list.

    A plain tag (e.g. "atlas") matches via exact membership, same as before.
    A pattern ending in ".*" (e.g. "atlas.*") is a prefix match against the
    tool's groups in their declared order (file-level groups first, then any
    per-entry groups) — it only matches tools where "atlas" leads the group
    path, not tools where "atlas" merely appears as a secondary tag.
    """
    if pattern.endswith(".*"):
        prefix = pattern[:-2].split(".")
        return groups[: len(prefix)] == prefix
    return pattern in groups


def can_access(user: UserModel, tool: ToolModel) -> bool:
    """returns true if user can access tool"""
    if not tool.groups or "public" in tool.groups:
        logger.debug("access granted to %s: public tool", tool.key)
        return True
    if user.is_admin:
        logger.debug("access granted to %s: %s is admin", tool.key, user.username)
        return True
    if any(_group_matches(g, tool.groups) for g in user.groups):
        logger.debug(
            "access granted to %s: group overlap for %s", tool.key, user.username
        )
        return True
    if tool.key in user.tools:
        logger.debug(
            "access granted to %s: explicit grant for %s", tool.key, user.username
        )
        return True
    logger.debug(
        "access denied to %s: %s has no matching group or grant",
        tool.key,
        user.username,
    )
    return False


def whoami_info(user: UserModel) -> dict:
    """Assembles a user's identity + accessible-tool-keys summary.

    Shared by the whoami MCP tool (renders as text) and the /whoami HTTP route
    (renders as JSON), so both surfaces report the same fields. Callers handle
    the unauthenticated case themselves before calling this.
    """
    accessible = [t.key for t in user.accessible_tools]
    return {
        "username": user.username,
        "email": user.email,
        "groups": user.groups,
        "tools": accessible,
    }


async def _attach_key_prefix(user: UserModel) -> UserModel:
    """Attaches the resolved user's current API key prefix, if any, regardless
    of which auth backend authenticated this request — a user who normally
    logs in via OAuth/JWT may still have a provisioned API key on file. Keys
    are stored one per user, keyed by username, so this is a direct lookup.
    """
    async with KeysIndex() as idx:
        record = await idx.get(user.username)
    if record:
        user.key = {"prefix": record["prefix"]}
    return user


async def get_current_user() -> UserModel | None:
    """resolves auth identity to a UserModel; prefers email, falls back to login.

    With claims.roles_claim set, groups derived from the token's roles are
    unioned into the matched record, or form a record-less user keyed by email.
    """

    try:
        token = await get_user_context()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Error getting user context: %s", exc)
        return None
    if token is None:
        logger.warning("No token returned from auth backend")
        return None
    if isinstance(token, UserModel):
        logger.debug("resolved user directly from token: %s", token.username)
        return token
    claims: dict = getattr(token, "claims", {}) or {}
    logger.info("auth token claims: %s", claims)
    claim_email = claims.get("email")
    email = (
        claim_email.lower() if isinstance(claim_email, str) and claim_email else None
    )
    logger.debug(
        "resolving user: email claim=%r (lowercased %r), login claim=%r",
        claim_email,
        email,
        claims.get("login"),
    )
    user: UserModel | None = None
    try:
        if email:
            user = await get_user_by_email(email)
            logger.info("email lookup for %s -> %s", email, user)
            if user:
                logger.debug("resolved user by email: %s", user.username)
        if user is None and (login := claims.get("login")):
            user = await get_user_by_username(login)
            if user:
                logger.debug("resolved user by login: %s", user.username)
        if user:
            user = await _attach_key_prefix(user)
    except Exception as e:  # noqa: BLE001
        # Claim groups can still authorize the caller; an unreachable store
        # only drops the record's extras, never grants more.
        logger.warning("User store unavailable, continuing with claims only: %s", e)
        user = None
    claim_groups = _verified_claim_groups(claims)
    if user:
        record_groups = list(user.groups)
        user.groups = user.groups + [g for g in claim_groups if g not in user.groups]
        logger.debug(
            "union for %s: record groups=%s + claim groups=%s -> %s",
            user.username,
            record_groups,
            claim_groups,
            user.groups,
        )
        return user
    if claim_groups and email:
        logger.debug("resolved claims-only user %s with groups %s", email, claim_groups)
        return UserModel(username=email, email=email, groups=claim_groups)
    if claim_groups and not email:
        logger.debug("claim groups %s dropped: token has no email claim", claim_groups)
    if settings.claims.roles_claim:
        logger.info(
            "%s authenticated but has no user record and no matching roles; "
            "treating as anonymous",
            email or claims.get("login"),
        )
    return None


async def get_user_by_key(
    raw_key: str, groups: list[str] | None = None
) -> UserModel | None:
    """Resolves `raw_key` to a UserModel via the keys index directly.

    Independent of `settings.auth`/`get_provider()` — HTTP routes that gate on
    this always check the raw key against the mcc-keys index, so they don't
    inherit whatever OAuth/JWT backend the MCP transport is configured with.

    If `groups` is given, the resolved user must belong to at least one of
    them, unless they're an admin — same admin-bypass semantics as
    `can_access`. If `groups` is None, any successfully resolved user passes.
    Returns None for an invalid/expired/unknown key, an unknown username, or
    a user that doesn't satisfy `groups`.
    """
    record = await verify_api_key(raw_key)
    if record is None:
        return None
    user = await get_user_by_username(record["username"])
    if user is None:
        return None
    if (
        groups is not None
        and not user.is_admin
        and not any(g in user.groups for g in groups)
    ):
        return None
    user.key = {"prefix": record["prefix"]}
    return user
