"""library_name resolution via the Emby /Items/{id}/Ancestors API."""
import logging

from core.http_client import get_internal_client

from ._cache import _cache_lib, _item_lib_cache, _normalize_library_name

logger = logging.getLogger("mediakeeper.stats.collector")


async def _resolve_library_name(
    item_id: str,
    url: str,
    api_key: str,
    library_aliases: dict | None = None,
) -> str | None:
    """Resolve the library_name of an item via the Emby /Items/{id}/Ancestors API."""
    if not item_id or not url:
        return None
    if item_id in _item_lib_cache:
        return _item_lib_cache[item_id]
    try:
        client = get_internal_client()
        res = await client.get(
            f"{url}/Items/{item_id}/Ancestors",
            headers={"X-Emby-Token": api_key},
            timeout=5.0,
        )
        if res.status_code == 200:
            ancestors = res.json()
            for a in ancestors:
                if a.get("Type") == "CollectionFolder":
                    lib_name = a.get("Name", "")
                    if lib_name:
                        _cache_lib(item_id, lib_name)
                        return lib_name
            for a in ancestors:
                if a.get("Type") == "Folder" and a.get("Name") != "root":
                    folder_name = a.get("Name", "")
                    folder_id = str(a.get("Id", ""))
                    if library_aliases and folder_id:
                        cached_name = library_aliases["by_id"].get(folder_id)
                        if cached_name:
                            _cache_lib(item_id, cached_name)
                            return cached_name
                    if library_aliases:
                        normalized_name = _normalize_library_name(folder_name)
                        cached_name = library_aliases["by_name"].get(normalized_name)
                        if cached_name:
                            _cache_lib(item_id, cached_name)
                            return cached_name
                    _cache_lib(item_id, folder_name)
                    return folder_name
    except Exception as e:
        logger.warning(f"Error _resolve_library_name({item_id}): {e}")
    return None
