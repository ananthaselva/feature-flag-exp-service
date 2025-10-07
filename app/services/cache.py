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
flag_cache = TTLCache(ttl_seconds=60)
FLAG_CACHE_PREFIX = "flag:"


def get_flag_cache_key(tenant: str, key: str) -> str:
    """Construct a consistent cache key for a flag"""
    return f"{FLAG_CACHE_PREFIX}{tenant}:{key}"


def invalidate_flag_cache(tenant: str, key: str) -> None:
    """Remove a specific flag from the cache"""
    cache_key = get_flag_cache_key(tenant, key)
    flag_cache.invalidate_prefix(cache_key)


# ----- Singleton instance for segments -----
segment_cache = TTLCache(ttl_seconds=120)
SEGMENT_CACHE_PREFIX = "segment:"


def get_segment_cache_key(tenant: str, segment_name: str) -> str:
    """Construct a consistent cache key for a segment"""
    return f"{SEGMENT_CACHE_PREFIX}{tenant}:{segment_name}"


def get_segment_from_cache(tenant: str, segment_name: str):
    """Return cached segment data if available and not expired"""
    cache_key = get_segment_cache_key(tenant, segment_name)
    return segment_cache.get(cache_key)


def set_segment_cache(tenant: str, segment_name: str, data: Any):
    """Store segment data in cache"""
    cache_key = get_segment_cache_key(tenant, segment_name)
    segment_cache.set(cache_key, data)


def invalidate_segment_cache(
    tenant: str | None = None, segment_name: str | None = None
):
    """Invalidate segment cache entries.

    - If both tenant and segment_name are provided → remove that specific cache key
    - If only tenant is provided → remove all segments for that tenant
    - If neither is provided → clear all segment caches
    """
    if tenant and segment_name:
        cache_key = get_segment_cache_key(tenant, segment_name)
        segment_cache.invalidate_prefix(cache_key)
    elif tenant:
        segment_cache.invalidate_prefix(f"{SEGMENT_CACHE_PREFIX}{tenant}:")
    else:
        segment_cache.invalidate_prefix(SEGMENT_CACHE_PREFIX)
