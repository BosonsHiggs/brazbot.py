"""
In-memory cache system with Time-To-Live (TTL) expiration and optional size cap.
"""

import time
from typing import Any, Dict, List, Optional


class Cache:
    """
    In-memory cache manager supporting TTL expiration (in seconds) and automatic cleanup.
    Accepts both `ttl=` and `seconds=` keyword arguments for backwards compatibility.
    """

    def __init__(self, default_ttl: float = 300.0, max_size: int = 10000):
        self.default_ttl = float(default_ttl)
        self.max_size = max_size
        self.cache: Dict[str, Any] = {}
        self.expiry_times: Dict[str, float] = {}

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
        seconds: Optional[float] = None,
    ) -> None:
        """Stores a value in the cache with an expiration time in seconds."""
        if len(self.cache) >= self.max_size and key not in self.cache:
            self.cleanup()
            if len(self.cache) >= self.max_size:
                oldest_key = min(self.expiry_times, key=self.expiry_times.get)  # type: ignore[arg-type]
                self.delete(oldest_key)

        effective_ttl = ttl if ttl is not None else (seconds if seconds is not None else self.default_ttl)
        self.cache[key] = value
        self.expiry_times[key] = time.time() + float(effective_ttl)

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieves a cached value if it exists and has not expired."""
        if key in self.cache:
            if time.time() < self.expiry_times.get(key, 0):
                return self.cache[key]
            self.delete(key)
        return default

    def get_remaining_ttl(self, key: str) -> float:
        """Returns the remaining time (in seconds) before the key expires, or 0.0."""
        if key in self.cache:
            rem = self.expiry_times.get(key, 0) - time.time()
            if rem > 0:
                return rem
            self.delete(key)
        return 0.0

    def update(self, key: str, value: Any) -> bool:
        """Updates the value of an existing key while preserving its current TTL."""
        if key in self.cache and time.time() < self.expiry_times.get(key, 0):
            self.cache[key] = value
            return True
        return False

    def delete(self, key: str) -> None:
        """Deletes a key from the cache."""
        self.cache.pop(key, None)
        self.expiry_times.pop(key, None)

    def clear(self) -> None:
        """Clears all entries from the cache."""
        self.cache.clear()
        self.expiry_times.clear()

    def cleanup(self) -> int:
        """Removes all expired keys and returns the number of removed entries."""
        now = time.time()
        expired_keys: List[str] = [
            k for k, exp in list(self.expiry_times.items()) if exp <= now
        ]
        for k in expired_keys:
            self.delete(k)
        return len(expired_keys)

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None

    def __len__(self) -> int:
        self.cleanup()
        return len(self.cache)
