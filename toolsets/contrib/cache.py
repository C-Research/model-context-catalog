import time
from collections import defaultdict

from mcc.cache import cache


async def cache_stats() -> dict:
    """Return cache statistics: summary and per-key size and TTL."""
    count = await cache.get_keys_count()
    backend = type(cache._get_backend("")).__name__ if count else "unknown"

    keys = []
    total_size = 0
    by_type: dict = defaultdict(lambda: {"count": 0, "size_bytes": 0})

    async for key in cache.scan("*"):
        expires_in = await cache.get_expire(key)
        size_bytes = await cache.get_size(key)
        total_size += size_bytes
        prefix = key.split(":")[0]
        by_type[prefix]["count"] += 1
        by_type[prefix]["size_bytes"] += size_bytes
        keys.append({
            "key": key,
            "size_bytes": size_bytes,
            "expires_in": expires_in,
            "expire_at": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ",
                time.gmtime(time.time() + expires_in),
            ) if expires_in is not None else None,
        })

    keys.sort(key=lambda e: e["key"])
    return {
        "summary": {
            "keys_count": count,
            "total_size_bytes": total_size,
            "backend": backend,
            "by_type": dict(by_type),
        },
        "keys": keys,
    }
