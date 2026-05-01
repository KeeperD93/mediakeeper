"""Browse Emby : libraries et contenus with statut sous-titres par langue."""
from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_internal_client
from ._constants import logger
from ._lang import _normalize_lang


async def get_emby_libraries(db: AsyncSession) -> list[dict]:
    """Return la liste des libraries Emby."""
    from services.emby import _get_emby_config
    cfg = await _get_emby_config(db)
    if not cfg:
        return []
    url, api_key = cfg
    headers = {"X-Emby-Token": api_key}
    try:
        client = get_internal_client()
        res = await client.get(f"{url}/Library/VirtualFolders", headers=headers, timeout=10.0)
        if res.status_code != 200:
            return []
        return [{"id": vf.get("ItemId", ""), "name": vf.get("Name", "")}
                for vf in res.json() if vf.get("Name")]
    except Exception as e:
        logger.error(f"[opensubtitles] Get libraries error: {e}")
        return []


async def browse_library(
    db: AsyncSession,
    start_index: int = 0,
    limit: int = 50,
    item_types: str = "Movie,Episode",
    search: str = "",
    parent_id: str = "",
    languages: list[str] | None = None,
    status_filter: str = "",
) -> dict:
    """Browse la library Emby with le statut sous-titres par langue.
    status_filter: '' (all), 'missing' (au moins 1 langue missing), 'complete' (all presentes)
    """
    from services.emby import _get_emby_config

    if languages is None:
        from services.subtitle_profiles import get_default_profile_languages
        languages = await get_default_profile_languages(db) or ["fre", "eng"]
    languages = [_normalize_lang(lang) for lang in languages if lang.strip()]

    cfg = await _get_emby_config(db)
    if not cfg:
        return {"items": [], "total": 0}

    url, api_key = cfg
    headers = {"X-Emby-Token": api_key}
    client = get_internal_client()

    _series_imdb_cache: dict[str, str] = {}

    async def _parse_items(raw_items: list) -> list[dict]:
        """Parse les items bruts Emby en dicts enrichis."""
        parsed = []
        for raw in raw_items:
            sources = raw.get("MediaSources") or []
            file_path = sources[0].get("Path", "") if sources else ""

            sub_langs = set()
            if sources:
                for s in sources[0].get("MediaStreams", []):
                    if s.get("Type") == "Subtitle":
                        lang = (s.get("Language") or "").strip()
                        if lang:
                            sub_langs.add(_normalize_lang(lang))

            sub_status = {lang: (lang in sub_langs) for lang in languages}
            providers = raw.get("ProviderIds") or {}
            imdb_id = providers.get("Imdb", "")
            poster_id = raw.get("SeriesId") or raw.get("Id", "") if raw.get("Type") == "Episode" else raw.get("Id", "")

            series_imdb_id = ""
            if raw.get("Type") == "Episode":
                series_id = raw.get("SeriesId", "")
                if series_id:
                    if series_id in _series_imdb_cache:
                        series_imdb_id = _series_imdb_cache[series_id]
                    else:
                        try:
                            sr = await client.get(
                                f"{url}/Items/{series_id}",
                                params={"Fields": "ProviderIds"},
                                headers=headers, timeout=8.0,
                            )
                            if sr.status_code == 200:
                                sp = sr.json().get("ProviderIds") or {}
                                series_imdb_id = sp.get("Imdb", "")
                            _series_imdb_cache[series_id] = series_imdb_id
                        except Exception:
                            _series_imdb_cache[series_id] = ""

            parsed.append({
                "item_id": raw.get("Id", ""),
                "poster_id": poster_id,
                "name": raw.get("Name", ""),
                "type": raw.get("Type", ""),
                "series_name": raw.get("SeriesName"),
                "season": raw.get("ParentIndexNumber"),
                "episode": raw.get("IndexNumber"),
                "year": raw.get("ProductionYear"),
                "file_path": file_path,
                "tmdb_id": providers.get("Tmdb", ""),
                "imdb_id": imdb_id,
                "series_imdb_id": series_imdb_id,
                "subtitle_status": sub_status,
                "existing_count": len(sub_langs),
            })
        return parsed

    def _matches_status(item: dict) -> bool:
        all_ok = all(item["subtitle_status"].values())
        if status_filter == "missing":
            return not all_ok
        if status_filter == "complete":
            return all_ok
        return True

    try:
        if not status_filter:
            params = {
                "IncludeItemTypes": item_types, "Recursive": "true",
                "Fields": "MediaSources,MediaStreams,Path,ProviderIds",
                "SortBy": "SortName", "SortOrder": "Ascending",
                "StartIndex": start_index, "Limit": limit,
                "EnableImageTypes": "Primary",
            }
            if search: params["SearchTerm"] = search
            if parent_id: params["ParentId"] = parent_id

            res = await client.get(f"{url}/Items", params=params, headers=headers, timeout=30.0)
            if res.status_code != 200:
                return {"items": [], "total": 0}

            data = res.json()
            items = await _parse_items(data.get("Items", []))
            return {"items": items, "total": data.get("TotalRecordCount", 0)}

        batch_size = 200
        emby_offset = 0
        matched = []
        total_matched = 0
        need_skip = start_index
        need_collect = limit
        emby_scanned = 0

        count_params = {
            "IncludeItemTypes": item_types, "Recursive": "true", "Limit": 0,
        }
        if search: count_params["SearchTerm"] = search
        if parent_id: count_params["ParentId"] = parent_id
        count_res = await client.get(f"{url}/Items", params=count_params, headers=headers, timeout=15.0)
        emby_total = count_res.json().get("TotalRecordCount", 0) if count_res.status_code == 200 else 0

        while emby_offset < emby_total and need_collect > 0:
            params = {
                "IncludeItemTypes": item_types, "Recursive": "true",
                "Fields": "MediaSources,MediaStreams,Path,ProviderIds",
                "SortBy": "SortName", "SortOrder": "Ascending",
                "StartIndex": emby_offset, "Limit": batch_size,
                "EnableImageTypes": "Primary",
            }
            if search: params["SearchTerm"] = search
            if parent_id: params["ParentId"] = parent_id

            res = await client.get(f"{url}/Items", params=params, headers=headers, timeout=30.0)
            if res.status_code != 200:
                break

            raw_items = res.json().get("Items", [])
            if not raw_items:
                break

            parsed = await _parse_items(raw_items)
            emby_scanned += len(parsed)

            for item in parsed:
                if _matches_status(item):
                    total_matched += 1
                    if need_skip > 0:
                        need_skip -= 1
                    elif need_collect > 0:
                        matched.append(item)
                        need_collect -= 1

            emby_offset += batch_size

        if emby_scanned > 0 and emby_offset < emby_total:
            ratio = total_matched / emby_scanned
            estimated_total = int(ratio * emby_total)
        else:
            estimated_total = total_matched

        return {"items": matched, "total": estimated_total}

    except Exception as e:
        logger.error(f"[subtitles] Browse library error: {e}")
        return {"items": [], "total": 0}
