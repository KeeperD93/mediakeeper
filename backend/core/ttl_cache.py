"""
Async-safe in-memory TTL cache.

Intended for short-lived caching of expensive, server-global read paths
(e.g. TMDB list endpoints) where staleness of a few minutes is acceptable.

Key design points:
  - Per-instance TTL, one instance per logical dataset.
  - Lock is only taken on miss, so hot reads stay lock-free.
  - The decorator variant ignores the first positional argument (assumed
    to be the DB session) when building the cache key, so sessions from
    different requests don't fragment the cache.
"""
import asyncio
import time
from functools import wraps
from typing import Any, Awaitable, Callable


class TTLCache:
    def __init__(self, ttl_seconds: float):
        self.ttl = float(ttl_seconds)
        self._data: dict[str, tuple[float, Any]] = {}
        self._lock = asyncio.Lock()

    async def get_or_set(
        self, key: str, factory: Callable[[], Awaitable[Any]],
    ) -> Any:
        now = time.monotonic()
        entry = self._data.get(key)
        if entry is not None and (now - entry[0]) < self.ttl:
            return entry[1]
        async with self._lock:
            entry = self._data.get(key)
            if entry is not None and (time.monotonic() - entry[0]) < self.ttl:
                return entry[1]
            value = await factory()
            self._data[key] = (time.monotonic(), value)
            return value

    def invalidate(self, key: str | None = None) -> None:
        if key is None:
            self._data.clear()
        else:
            self._data.pop(key, None)


def cached_tmdb_list(ttl_seconds: float = 900):
    """
    Decorator for async functions shaped as ``fn(db, *args, **kwargs)``.

    The first positional argument (the DB session) is excluded from the
    cache key — only the remaining args/kwargs and the function's qualified
    name contribute. Each decorated function gets its own isolated cache.

    Typical use: TMDB list endpoints where the output depends on page /
    provider_id / media_type but not on the calling user or session.
    """
    def deco(fn: Callable[..., Awaitable[Any]]):
        cache = TTLCache(ttl_seconds)
        name = getattr(fn, "__qualname__", fn.__name__)

        @wraps(fn)
        async def wrapper(db, *args, **kwargs):
            parts = [name, *(repr(a) for a in args)]
            for k in sorted(kwargs.keys()):
                parts.append(f"{k}={kwargs[k]!r}")
            key = "|".join(parts)

            async def factory():
                return await fn(db, *args, **kwargs)

            return await cache.get_or_set(key, factory)

        wrapper._cache = cache  # exposed for tests / manual invalidation
        return wrapper

    return deco
