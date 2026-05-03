import time
from typing import Any, Optional


class TTLCache:
    def __init__(self, ttl_seconds: int = 1800):  # 30 minutes default
        self._store: dict[str, tuple[Any, float]] = {}
        self.ttl = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry:
            value, ts = entry
            if time.time() - ts < self.ttl:
                return value
            del self._store[key]
        return None

    def set(self, key: str, value: Any):
        self._store[key] = (value, time.time())

    def timestamp(self, key: str) -> Optional[float]:
        entry = self._store.get(key)
        return entry[1] if entry else None


cache = TTLCache(ttl_seconds=3600)
