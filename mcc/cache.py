import hashlib
import json
import re
from typing import Any, Awaitable, Callable

from cashews import cache

from mcc.settings import settings

_MISS = object()

_RATE_LIMIT_RE = re.compile(r"^(\d+)/(\d+)(s|min|hr)$")
_RATE_LIMIT_UNIT_SECONDS = {"s": 1, "min": 60, "hr": 3600}


cfg = settings.get("cache", {})
backend = cfg.get("backend", "mem://")
cache.setup(backend)


def params_hash(params: dict | None) -> str:
    serialized = json.dumps(params or {}, sort_keys=True)
    return hashlib.sha256(serialized.encode()).hexdigest()[:16]


async def cached(
    key: str | None, compute: Callable[[], Awaitable[Any]], expire: int | None
) -> Any:
    """Return the cached value for key, else compute it and store it under key.

    On a hit, returns the stored value without calling compute. On a miss,
    awaits compute(), stores the result with the given expiry, and returns it.
    When key is None (caching disabled) compute() is awaited directly with no
    cache I/O.

    Hits are distinguished from misses with a sentinel default rather than a
    falsy check, so a cached value that is itself falsy (None, "", 0) is still
    returned from the cache instead of triggering recomputation.
    """
    if key is None:
        return await compute()
    value = await cache.get(key, default=_MISS)
    if value is not _MISS:
        return value
    value = await compute()
    await cache.set(key, value, expire=expire)
    return value


def parse_rate_limit(value: int | str) -> tuple[int, int]:
    """Parse a rate_limit.yaml value into (limit, period_seconds).

    Accepts the int -1 (unlimited — period is meaningless, returned as 0) or a
    "<count>/<n><unit>" string with unit s|min|hr, e.g. "60/1min", "50/24hr",
    "10/30s". Raises ValueError on anything else, so a typo'd settings.yaml
    entry fails at middleware construction time, not on a live request.
    """
    if value == -1:
        return -1, 0
    match = _RATE_LIMIT_RE.match(str(value)) if isinstance(value, str) else None
    if not match:
        raise ValueError(
            f"Invalid rate limit {value!r}: expected -1 or '<count>/<n><unit>' "
            "with unit s|min|hr, e.g. '60/1min'"
        )
    count, n, unit = match.groups()
    return int(count), int(n) * _RATE_LIMIT_UNIT_SECONDS[unit]


async def over_limit(key: str, limit: int, period: int) -> tuple[bool, int]:
    """Fixed-window rate check: increment key's counter, capped to `period` seconds.

    Returns (is_over_limit, seconds_remaining_in_window). A limit of -1 means
    unlimited — always returns (False, 0) without touching the cache. The
    window resets `period` seconds after the first increment recorded in it
    (cashews' backend.incr sets the TTL only on that first increment), so this
    is a genuine fixed window, not a sliding average.
    """
    if limit == -1:
        return False, 0
    count = await cache.incr(key, expire=period)
    remaining = await cache.get_expire(key)
    return count > limit, remaining
