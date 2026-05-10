"""Emby data access for the watchlist (libraries, series, episodes)."""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_internal_client
from services.emby import _get_emby_config
from services.portal.iso_lang_map import to_display_code

logger = logging.getLogger("mediakeeper.watchlist.scanner")

# Cap the per-episode language list to keep the scan_results JSON bounded
# even on multi-dub releases. Five distinct dubs already covers the worst
# case observed in user libraries.
_MAX_AUDIO_LANGS_PER_EP = 5


def _extract_audio_languages(media_streams: list | None) -> list[str]:
    """Return ordered, de-duplicated 2-letter uppercase audio codes.

    Reads the ``MediaStreams`` array of an Emby episode item, keeps only
    audio streams, maps each one through ``to_display_code`` (which
    rejects empty/unknown codes), and preserves the first occurrence of
    each so the order matches the file's track order.
    """
    if not isinstance(media_streams, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for stream in media_streams:
        if not isinstance(stream, dict) or stream.get("Type") != "Audio":
            continue
        raw = stream.get("Language") or stream.get("LanguageCode") or ""
        code = to_display_code(raw)
        if not code or code in seen:
            continue
        seen.add(code)
        out.append(code)
        if len(out) >= _MAX_AUDIO_LANGS_PER_EP:
            break
    return out


async def get_series_libraries(db: AsyncSession) -> list[dict]:
    cfg = await _get_emby_config(db)
    if not cfg:
        return []
    url, ak = cfg
    try:
        r = await get_internal_client().get(f"{url}/Library/VirtualFolders", headers={"X-Emby-Token": ak}, timeout=15.0)
        return [{"id": f.get("ItemId", ""), "name": f.get("Name", ""), "collection_type": f.get("CollectionType", "")}
                for f in r.json() if f.get("CollectionType", "") in ("tvshows", "")] if r.status_code == 200 else []
    except Exception as e:
        logger.error(f"get_series_libraries: {e}")
        return []


async def _get_all_emby_series(db: AsyncSession, library_id: str = "") -> list[dict]:
    cfg = await _get_emby_config(db)
    if not cfg:
        return []
    url, ak = cfg
    params = {"IncludeItemTypes": "Series", "Recursive": "true",
              "Fields": "ProviderIds,Overview,PremiereDate,Status,ChildCount",
              "SortBy": "SortName", "SortOrder": "Ascending"}
    if library_id:
        params["ParentId"] = library_id
    try:
        r = await get_internal_client().get(f"{url}/Items", params=params, headers={"X-Emby-Token": ak}, timeout=30.0)
        return r.json().get("Items", []) if r.status_code == 200 else []
    except Exception as e:
        logger.error(f"_get_all_emby_series: {e}")
        return []


async def _get_emby_episodes(
    db: AsyncSession, series_id: str
) -> dict[tuple[int, int], list[str]]:
    """Return ``{(season, episode): [audio_lang, …]}`` for present episodes.

    Episodes without a resolvable season/episode index are skipped (no
    user-visible match anyway). The audio language list may be empty
    when Emby returns no audio streams for that file.
    """
    cfg = await _get_emby_config(db)
    if not cfg:
        return {}
    url, ak = cfg
    try:
        r = await get_internal_client().get(
            f"{url}/Shows/{series_id}/Episodes",
            params={"Fields": "PremiereDate,ProviderIds,MediaStreams"},
            headers={"X-Emby-Token": ak}, timeout=20.0)
        if r.status_code != 200:
            return {}
        out: dict[tuple[int, int], list[str]] = {}
        for ep in r.json().get("Items", []):
            sn = ep.get("ParentIndexNumber")
            en = ep.get("IndexNumber")
            if sn is None or en is None:
                continue
            out[(sn, en)] = _extract_audio_languages(ep.get("MediaStreams"))
        return out
    except Exception as e:
        logger.error(f"_get_emby_episodes: {e}")
        return {}
