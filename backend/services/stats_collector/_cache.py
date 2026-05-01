"""In-memory item_id -> library_name cache + normalization helpers."""

_MAX_LIB_CACHE = 10_000
_item_lib_cache: dict[str, str] = {}


def _normalize_library_name(name: str) -> str:
    return (
        (name or "")
        .lower()
        .replace(" ", "")
        .replace("&", "et")
        .replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
    )


def _cache_lib(item_id: str, lib_name: str):
    """Add to the cache, evicting if it grows too large."""
    if len(_item_lib_cache) >= _MAX_LIB_CACHE:
        keys = list(_item_lib_cache.keys())[: _MAX_LIB_CACHE // 4]
        for k in keys:
            del _item_lib_cache[k]
    _item_lib_cache[item_id] = lib_name
