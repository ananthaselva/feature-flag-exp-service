import time
from typing import Any

# ----- In-memory TTL cache -----
class TTLCache:
    def __init__(self, ttl_seconds: int = 30):
        self.ttl = ttl_seconds
        self.store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str):
        v = self.store.get(key)
        if not v:
            return None
        expires, data = v
        if time.time() > expires:
            self.store.pop(key, None)
            return None
        return data

    def set(self, key: str, value: Any):
        self.store[key] = (time.time() + self.ttl, value)

    def invalidate_prefix(self, prefix: str):
        for k in list(self.store.keys()):
            if k.startswith(prefix):
                self.store.pop(k, None)


# ----- Singleton instance for flags -----
flag_cache = TTLCache(ttl_seconds=60)  # adjust TTL as needed
FLAG_CACHE_PREFIX = "flag:"


def get_flag_cache_key(tenant: str, key: str) -> str:
    """Construct a consistent cache key for a flag"""
    return f"{FLAG_CACHE_PREFIX}{tenant}:{key}"


def invalidate_flag_cache(tenant: str, key: str) -> None:
    """Remove a specific flag from the cache"""
    cache_key = get_flag_cache_key(tenant, key)
    flag_cache.invalidate_prefix(cache_key)
