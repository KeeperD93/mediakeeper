"""library_name resolution via the Emby /Items/{id}/Ancestors API."""
import logging
from urllib.parse import quote

from core.http_client import get_internal_client

from ._cache import _cache_lib, _item_lib_cache, _normalize_library_name

logger = logging.getLogger("mediakeeper.stats.collector")


async def _fetch_ancestors(
    item_id: str, url: str, api_key: str, user_id: str | None = None
) -> list | None:
    """Raw Emby /Items/{id}/Ancestors list; None on missing args, error, non-200,
    or a non-list payload.

    ``user_id`` queries the ancestry *as that user*, which exposes the virtual
    CollectionFolder (the real library name) instead of the physical folder slug
    — without it Emby returns e.g. ``Folder 'filmsdanimation'`` rather than
    ``CollectionFolder "Films d'Animation"``.
    """
    if not item_id or not url:
        return None
    try:
        client = get_internal_client()
        query = f"{url}/Items/{quote(item_id, safe='')}/Ancestors"
        if user_id:
            query += f"?UserId={quote(user_id, safe='')}"
        res = await client.get(
            query,
            headers={"X-Emby-Token": api_key},
            timeout=5.0,
        )
        if res.status_code == 200:
            data = res.json()
            return data if isinstance(data, list) else None
    except Exception as e:
        logger.warning("Error _fetch_ancestors(%s): %s", item_id, e)
    return None


def _match_library_name(
    ancestors: list, library_aliases: dict | None = None
) -> tuple[str | None, bool]:
    """Pick the library name from an Ancestors list.

    Returns ``(name, resolved)``: ``resolved=True`` means a real Emby library (a
    CollectionFolder, or a folder whose id/name maps to a known library). A name
    with ``resolved=False`` means we fell back to a raw sub-folder name (the wrong
    label); ``(None, False)`` means nothing usable was found.
    """
    for a in ancestors:
        if a.get("Type") == "CollectionFolder":
            lib_name = a.get("Name", "")
            if lib_name:
                return lib_name, True
    for a in ancestors:
        if a.get("Type") == "Folder" and a.get("Name") != "root":
            folder_name = a.get("Name", "")
            folder_id = str(a.get("Id", ""))
            if library_aliases and folder_id:
                match = library_aliases["by_id"].get(folder_id)
                if match:
                    return match, True
            if library_aliases:
                match = library_aliases["by_name"].get(_normalize_library_name(folder_name))
                if match:
                    return match, True
            return folder_name, False
    return None, False


async def _resolve_library_name(
    item_id: str,
    url: str,
    api_key: str,
    library_aliases: dict | None = None,
    user_id: str | None = None,
) -> str | None:
    """Resolve the library_name of an item via the Emby /Items/{id}/Ancestors API."""
    if not item_id or not url:
        return None
    if item_id in _item_lib_cache:
        return _item_lib_cache[item_id]
    ancestors = await _fetch_ancestors(item_id, url, api_key, user_id)
    if ancestors is None:
        return None
    name, resolved = _match_library_name(ancestors, library_aliases)
    if name and not resolved:
        # Diagnostic: no CollectionFolder ancestor and no known library among the
        # folders — we fall back to a sub-folder name (the wrong label). Log the
        # ancestry so the cause can be identified from an install where this
        # happens.
        logger.warning(
            "library_name unresolved for item %s: no CollectionFolder ancestor, "
            "using folder %r. ancestors=%s",
            item_id, name,
            [(anc.get("Type"), anc.get("Name")) for anc in ancestors],
        )
    # Cache only a REAL library (resolved): the raw sub-folder fallback is
    # view-dependent (a no-user query returns a physical-folder slug), so caching
    # it by item_id alone would poison a later correct per-user resolution.
    if name and resolved:
        _cache_lib(item_id, name)
    return name


async def _session_library_name(
    np: dict,
    item_id: str,
    url: str,
    api_key: str,
    library_aliases: dict | None = None,
    user_id: str | None = None,
) -> str | None:
    """Best Emby library (CollectionFolder) name for a playing session item.

    Order: Emby's own ``LibraryName`` → resolve via the Ancestors API (walks
    up to the CollectionFolder, correct even for items nested in a sub-folder)
    → ``ParentName`` only as a last resort. ParentName is the immediate parent
    (a sub-folder, or a season for episodes), not the library — using it before
    the resolver was the "sub-folder shown instead of library" bug.

    ``user_id`` (the session's Emby user) is forwarded so the Ancestors query
    runs as that user and returns the virtual CollectionFolder.
    """
    return (
        np.get("LibraryName")
        or await _resolve_library_name(item_id, url, api_key, library_aliases, user_id)
        or np.get("ParentName")
        or None
    )


async def _emby_admin_user_id(url: str, api_key: str) -> str | None:
    """An Emby user id to query the ancestry 'as a user' — that view exposes the
    virtual CollectionFolder (real library name). Prefer an administrator (sees
    every library); fall back to the first user, or None. Used by the repair
    routine, which has no session user of its own.
    """
    if not url:
        return None
    try:
        client = get_internal_client()
        res = await client.get(
            f"{url}/Users", headers={"X-Emby-Token": api_key}, timeout=5.0
        )
        if res.status_code == 200:
            users = res.json()
            if isinstance(users, list) and users:
                chosen = next(
                    (u for u in users if u.get("Policy", {}).get("IsAdministrator")),
                    users[0],
                )
                return str(chosen.get("Id", "")) or None
    except Exception as e:
        logger.warning("Error _emby_admin_user_id: %s", e)
    return None
