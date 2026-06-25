import hashlib
import json
from typing import Any, Awaitable, Callable

from cashews import cache

from mcc.settings import settings

_MISS = object()


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
