"""Generic LRU cache primitives with TTL."""
import time
from collections import OrderedDict


_CACHE_MISS = object()


def _get_cached_blob(
    cache: "OrderedDict[str, tuple[float, tuple[bytes, str] | None]]",
    key: str,
) -> tuple[bytes, str] | None | object:
    cached = cache.get(key)
    if not cached:
        return _CACHE_MISS

    expires_at, payload = cached
    now = time.monotonic()
    if expires_at <= now:
        cache.pop(key, None)
        return _CACHE_MISS

    cache.move_to_end(key)
    return payload


def _store_cached_blob(
    cache: "OrderedDict[str, tuple[float, tuple[bytes, str] | None]]",
    key: str,
    payload: tuple[bytes, str] | None,
    *,
    ttl: int,
    max_entries: int,
) -> tuple[bytes, str] | None:
    cache[key] = (time.monotonic() + ttl, payload)
    cache.move_to_end(key)
    while len(cache) > max_entries:
        cache.popitem(last=False)
    return payload
