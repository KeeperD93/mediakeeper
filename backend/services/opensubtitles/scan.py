"""Scan Emby : recherche par streams et detection des media without sous-titres."""
from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_internal_client
from ._constants import logger, _IMAGE_CODECS
from ._lang import _normalize_lang


async def search_streams_in_library(
    db: AsyncSession,
    query: str = "",
    stream_type: str = "all",
    start: int = 0,
    limit: int = 50,
) -> dict:
    """Recherche les files dont les streams correspondent a la requete.

    Cherche in le titre et la langue des streams audio et sous-titres.
    Exemple: query="VFQ" trouvera les files with une piste audio/sub titree "VFQ".
    """
    from services.emby import _get_emby_config

    cfg = await _get_emby_config(db)
    if not cfg:
        return {"items": [], "total": 0}

    url, api_key = cfg
    headers = {"X-Emby-Token": api_key}
    client = get_internal_client()

    q = query.lower().strip()
    if not q:
        return {"items": [], "total": 0}

    batch_size = 200
    emby_offset = 0
    matched = []
    need_skip = start
    need_collect = limit

    try:
        count_res = await client.get(f"{url}/Items", params={
            "IncludeItemTypes": "Movie,Episode",
            "Recursive": "true", "Limit": 0,
        }, headers=headers, timeout=15.0)
        emby_total = count_res.json().get("TotalRecordCount", 0) if count_res.status_code == 200 else 0
    except Exception:
        emby_total = 0

    total_matched = 0
    emby_scanned = 0

    while emby_offset < emby_total and need_collect > 0:
        try:
            res = await client.get(f"{url}/Items", params={
                "IncludeItemTypes": "Movie,Episode",
                "Recursive": "true",
                "Fields": "MediaSources,MediaStreams,Path",
                "SortBy": "SortName", "SortOrder": "Ascending",
                "StartIndex": emby_offset, "Limit": batch_size,
            }, headers=headers, timeout=30.0)

            if res.status_code != 200:
                break

            raw_items = res.json().get("Items", [])
            if not raw_items:
                break
            emby_scanned += len(raw_items)

            for item in raw_items:
                sources = item.get("MediaSources") or []
                if not sources:
                    continue

                streams_data = sources[0].get("MediaStreams") or []
                if not streams_data:
                    streams_data = item.get("MediaStreams") or []

                matching_streams = []
                for s in streams_data:
                    s_type = s.get("Type", "").lower()

                    if stream_type == "audio" and s_type != "audio":
                        continue
                    if stream_type == "subtitle" and s_type != "subtitle":
                        continue
                    if s_type not in ("audio", "subtitle"):
                        continue

                    lang = (s.get("Language") or "").lower()
                    title = (s.get("Title") or "").lower()
                    display = (s.get("DisplayTitle") or "").lower()
                    codec = (s.get("Codec") or "").lower()

                    if q in lang or q in title or q in display or q in codec:
                        channels = s.get("Channels", 0)
                        matching_streams.append({
                            "index": s.get("Index", 0),
                            "type": s_type,
                            "language": s.get("Language") or "?",
                            "title": s.get("Title") or s.get("DisplayTitle") or "",
                            "codec": s.get("Codec", ""),
                            "channels": channels if s_type == "audio" else 0,
                            "is_default": s.get("IsDefault", False),
                            "is_forced": s.get("IsForced", False),
                            "is_external": s.get("IsExternal", False),
                        })

                if matching_streams:
                    total_matched += 1
                    if need_skip > 0:
                        need_skip -= 1
                    elif need_collect > 0:
                        file_path = sources[0].get("Path", "")
                        poster_id = item.get("SeriesId") or item.get("Id", "") if item.get("Type") == "Episode" else item.get("Id", "")
                        matched.append({
                            "item_id": item.get("Id", ""),
                            "poster_id": poster_id,
                            "name": item.get("Name", ""),
                            "type": item.get("Type", ""),
                            "series_name": item.get("SeriesName"),
                            "season": item.get("ParentIndexNumber"),
                            "episode": item.get("IndexNumber"),
                            "year": item.get("ProductionYear"),
                            "file_path": file_path,
                            "matching_streams": matching_streams,
                        })
                        need_collect -= 1

        except Exception as e:
            logger.error(f"[opensubtitles] search_streams error at offset {emby_offset}: {e}")

        emby_offset += batch_size

    if emby_scanned > 0 and emby_offset < emby_total:
        estimated = int((total_matched / emby_scanned) * emby_total)
    else:
        estimated = total_matched

    return {"items": matched, "total": estimated}


async def scan_missing_subtitles(
    db: AsyncSession,
    languages: list[str] = None,
    library: str = "",
) -> list[dict]:
    """Emby scan to find media without subtitles in the requested languages."""
    from services.emby import _get_emby_config

    if languages is None:
        from services.subtitle_profiles import get_default_profile_languages
        languages = await get_default_profile_languages(db) or ["fre", "eng"]

    languages = [_normalize_lang(lang) for lang in languages if lang.strip()]
    if not languages:
        from services.subtitle_profiles import get_default_profile_languages
        languages = await get_default_profile_languages(db) or ["fre", "eng"]

    cfg = await _get_emby_config(db)
    if not cfg:
        logger.warning("[opensubtitles] Scan missing: Emby not configured")
        return []

    url, api_key = cfg
    headers = {"X-Emby-Token": api_key}
    client = get_internal_client()

    lib_map = {}
    try:
        libs_res = await client.get(f"{url}/Library/VirtualFolders", headers=headers, timeout=10.0)
        if libs_res.status_code == 200:
            for vf in libs_res.json():
                vf_name = vf.get("Name", "")
                vf_id = vf.get("ItemId", "")
                if vf_id and vf_name:
                    lib_map[vf_id] = vf_name
    except Exception:
        logger.warning("[opensubtitles] Could not load Emby libraries for mapping")

    try:
        count_res = await client.get(f"{url}/Items", params={
            "IncludeItemTypes": "Movie,Episode",
            "Recursive": "true",
            "Limit": 0,
        }, headers=headers, timeout=15.0)
        total_items = count_res.json().get("TotalRecordCount", 0) if count_res.status_code == 200 else 0
    except Exception as e:
        logger.error(f"[opensubtitles] Count query failed: {e}")
        total_items = 0

    if total_items == 0:
        logger.info("[opensubtitles] Scan missing: no items found in Emby")
        return []

    logger.info(f"[opensubtitles] Scan missing: {total_items} items, languages={languages}")

    missing = []
    batch_size = 100

    for offset in range(0, total_items, batch_size):
        try:
            res = await client.get(f"{url}/Items", params={
                "IncludeItemTypes": "Movie,Episode",
                "Recursive": "true",
                "Fields": "MediaSources,MediaStreams,Path",
                "SortBy": "SortName",
                "SortOrder": "Ascending",
                "StartIndex": offset,
                "Limit": batch_size,
            }, headers=headers, timeout=30.0)

            if res.status_code != 200:
                logger.warning(f"[opensubtitles] Emby returned {res.status_code} at offset {offset}")
                continue

            data = res.json()
            items = data.get("Items", [])

            for item in items:
                sources = item.get("MediaSources") or []
                if not sources:
                    continue

                streams = sources[0].get("MediaStreams") or []
                sub_langs = set()
                for s in streams:
                    if s.get("Type") == "Subtitle":
                        codec = (s.get("Codec") or "").lower()
                        if codec in _IMAGE_CODECS:
                            continue
                        raw = (s.get("Language") or "").strip()
                        if raw:
                            sub_langs.add(_normalize_lang(raw))

                missing_langs = [lang for lang in languages if lang not in sub_langs]
                if missing_langs:
                    lib_name = ""
                    for ancestor_id in (item.get("ParentId", ""), item.get("LibraryId", "")):
                        if ancestor_id in lib_map:
                            lib_name = lib_map[ancestor_id]
                            break
                    if not lib_name:
                        lib_name = item.get("LibraryName") or ""

                    if library and lib_name != library:
                        continue

                    missing.append({
                        "item_id": item.get("Id", ""),
                        "item_name": item.get("Name", ""),
                        "item_type": item.get("Type", ""),
                        "series_name": item.get("SeriesName"),
                        "library": lib_name,
                        "file_path": sources[0].get("Path") or "",
                        "existing_subs": list(sub_langs),
                        "missing_langs": missing_langs,
                    })

        except Exception as e:
            logger.error(f"[opensubtitles] Scan error at offset {offset}: {e}")
            continue

    logger.info(f"[opensubtitles] Scan missing complete: {len(missing)} items without subtitles")
    return missing
