import time
from typing import Any


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
