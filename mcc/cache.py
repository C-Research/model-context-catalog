import hashlib
import json
from typing import Any

from cashews import cache

from mcc.settings import settings

_MISS = object()


cfg = settings.get("cache", {})
backend = cfg.get("backend", "mem://")
cache.setup(backend)


def params_hash(params: dict | None) -> str:
    serialized = json.dumps(params or {}, sort_keys=True)
    return hashlib.sha256(serialized.encode()).hexdigest()[:16]


async def get_or_miss(key: str) -> tuple[Any, bool]:
    """Fetch a cached value, distinguishing a stored value from a cache miss.

    Returns (value, missed): on a hit, (cached_value, False); on a miss,
    (None, True). This avoids ambiguity when the cached value is itself falsy
    (e.g. None, "", 0), which a plain default-based get() cannot disambiguate.
    """
    cached = await cache.get(key, default=_MISS)
    if cached is _MISS:
        return None, True
    return cached, False
