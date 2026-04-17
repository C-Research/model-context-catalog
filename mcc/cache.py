import hashlib
import json

from cashews import cache

from mcc.settings import settings

_MISS = object()


cfg = settings.get("cache", {})
backend = cfg.get("backend", "mem://")
cache.setup(backend)


def params_hash(params: dict | None) -> str:
    serialized = json.dumps(params or {}, sort_keys=True)
    return hashlib.sha256(serialized.encode()).hexdigest()[:16]
