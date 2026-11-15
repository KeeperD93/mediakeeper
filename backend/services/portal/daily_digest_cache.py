"""In-memory cache of the Portal daily digest payloads.

A payload is kept ~1h per (user_id, date, lang) triple so a viewer re-opening
the overlay, or navigating pages that remount the layout, doesn't trigger a
full re-aggregation.
"""
import time

_CACHE_TTL_SEC = 3600

# Cache: (user_id, date_iso, lang) -> (expires_at_epoch, payload). lang is part
# of the key because the payload re-resolves media titles/synopsis per viewer
# locale; a lang-agnostic key would serve the first-cached language to all.
_digest_cache: dict[tuple[int, str, str], tuple[float, dict]] = {}
# Moved by every drop: a payload built across a drop holds the old data, it is not cached.
_cache_generation = 0
# What a member's podium row shows the other readers: a change drops every payload.
PODIUM_FIELDS = (
    "display_name", "is_public", "avatar_url", "avatar_custom_path", "avatar_effect", "selected_title",
)


def generation() -> int:
    return _cache_generation


def get(user_id: int, date_iso: str, lang: str) -> dict | None:
    key = (user_id, date_iso, lang)
    hit = _digest_cache.get(key)
    if not hit:
        return None
    expires_at, payload = hit
    if expires_at < time.time():
        _digest_cache.pop(key, None)
        return None
    return payload


def put(user_id: int, date_iso: str, lang: str, payload: dict) -> None:
    _digest_cache[(user_id, date_iso, lang)] = (time.time() + _CACHE_TTL_SEC, payload)


def invalidate_cache(user_id: int) -> None:
    """Drop cached payload for a user (used on dismiss so reopens don't
    keep serving stale content)."""
    global _cache_generation
    _cache_generation += 1
    for key in list(_digest_cache.keys()):
        if key[0] == user_id:
            _digest_cache.pop(key, None)


def clear_cache() -> None:
    """Drop every cached payload: something a member shows the others changed
    (name, visibility, avatar, avatar effect, title), and any reader's podium
    may show them."""
    global _cache_generation
    _cache_generation += 1
    _digest_cache.clear()
