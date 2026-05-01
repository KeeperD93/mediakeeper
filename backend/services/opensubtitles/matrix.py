"""Matrice season × episode et counts availables OpenSubtitles."""
import time as _time

from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_internal_client, get_external_client

from . import auth
from ._constants import logger, OS_API_BASE, _IMAGE_CODECS
from ._lang import _normalize_lang

# Cache memory for les counts (1h TTL)
_os_count_cache: dict[str, tuple[int, float]] = {}
_OS_COUNT_TTL = 3600


async def get_series_matrix(
    db: AsyncSession,
    series_id: str,
    languages: list[str] | None = None,
) -> dict:
    """Return une matrice season×episode with le statut sous-titres par langue."""
    from services.emby import _get_emby_config

    if languages is None:
        from services.subtitle_profiles import get_default_profile_languages
        languages = await get_default_profile_languages(db) or ["fre", "eng"]
    languages = [_normalize_lang(lang) for lang in languages if lang.strip()]

    cfg = await _get_emby_config(db)
    if not cfg:
        return {"series_name": "", "seasons": {}, "languages": languages, "total_episodes": 0, "coverage": {}}

    url, api_key = cfg
    headers = {"X-Emby-Token": api_key}
    client = get_internal_client()

    try:
        series_res = await client.get(
            f"{url}/Items/{series_id}",
            headers=headers, timeout=8.0,
        )
        series_name = series_res.json().get("Name", "") if series_res.status_code == 200 else ""

        res = await client.get(f"{url}/Items", params={
            "ParentId": series_id,
            "IncludeItemTypes": "Episode",
            "Recursive": "true",
            "Fields": "MediaSources,MediaStreams,ParentIndexNumber,IndexNumber",
            "SortBy": "ParentIndexNumber,IndexNumber",
            "SortOrder": "Ascending",
            "Limit": "500",
        }, headers=headers, timeout=30.0)

        if res.status_code != 200:
            return {"series_name": series_name, "seasons": {}, "languages": languages, "total_episodes": 0, "coverage": {}}

        data = res.json()
        seasons = {}
        total_episodes = 0
        lang_counts = {lang: 0 for lang in languages}

        for ep in data.get("Items", []):
            s_num = ep.get("ParentIndexNumber") or 0
            e_num = ep.get("IndexNumber") or 0
            if s_num == 0 or e_num == 0:
                continue

            sources = ep.get("MediaSources") or []
            sub_langs = set()
            if sources:
                for s in sources[0].get("MediaStreams", []):
                    if s.get("Type") == "Subtitle":
                        codec = (s.get("Codec") or "").lower()
                        if codec in _IMAGE_CODECS:
                            continue
                        lang = (s.get("Language") or "").strip()
                        if lang:
                            sub_langs.add(_normalize_lang(lang))

            s_key = str(s_num)
            if s_key not in seasons:
                seasons[s_key] = {"episodes": {}}

            ep_status = {lang: (lang in sub_langs) for lang in languages}
            seasons[s_key]["episodes"][str(e_num)] = {
                "status": ep_status,
                "item_id": ep.get("Id", ""),
                "name": ep.get("Name", ""),
            }

            total_episodes += 1
            for lang in languages:
                if lang in sub_langs:
                    lang_counts[lang] += 1

        coverage = {}
        for lang in languages:
            coverage[lang] = round((lang_counts[lang] / total_episodes) * 100, 1) if total_episodes > 0 else 0

        return {
            "series_name": series_name,
            "seasons": seasons,
            "languages": languages,
            "total_episodes": total_episodes,
            "coverage": coverage,
        }

    except Exception as e:
        logger.error(f"[subtitles] Series matrix error: {e}")
        return {"series_name": "", "seasons": {}, "languages": languages, "total_episodes": 0, "coverage": {}}


async def get_available_counts(db: AsyncSession, items: list[dict]) -> dict:
    """Return le number de sous-titres availables sur OpenSubtitles for each item.
    items: [{"imdb_id": "tt123", "tmdb_id": "456", "type": "Movie"}, ...]
    Return: {"tt123": 47, "456": 12, ...}
    """
    headers = await auth._get_headers(db)
    if not headers:
        return {}

    counts = {}
    client = get_external_client()
    now = _time.time()

    for item in items[:10]:
        cache_key = item.get("imdb_id") or item.get("tmdb_id") or ""
        if not cache_key:
            continue

        if cache_key in _os_count_cache:
            cached_count, cached_at = _os_count_cache[cache_key]
            if now - cached_at < _OS_COUNT_TTL:
                counts[cache_key] = cached_count
                continue

        from services.subtitle_profiles import get_default_profile_languages
        prof_langs = await get_default_profile_languages(db)
        lang_map = {"fre": "fr", "eng": "en", "spa": "es", "ger": "de", "ita": "it", "por": "pt", "jpn": "ja", "chi": "zh", "kor": "ko", "rus": "ru", "ara": "ar", "nld": "nl", "pol": "pl", "tur": "tr", "swe": "sv", "dan": "da", "nor": "no", "fin": "fi", "ron": "ro", "hun": "hu", "ell": "el", "heb": "he", "tha": "th", "vie": "vi", "ind": "id", "ukr": "uk", "hin": "hi", "ces": "cs"}
        params = {"languages": ",".join(lang_map.get(lang, lang[:2]) for lang in (prof_langs or ["fre", "eng"]))}
        if item.get("imdb_id"):
            params["imdb_id"] = item["imdb_id"].replace("tt", "")
        elif item.get("tmdb_id"):
            params["tmdb_id"] = item["tmdb_id"]

        try:
            res = await client.get(
                f"{OS_API_BASE}/subtitles",
                params=params,
                headers=headers,
                timeout=10.0,
            )
            if res.status_code == 200:
                total = res.json().get("total_count", 0)
                counts[cache_key] = total
                _os_count_cache[cache_key] = (total, now)
            else:
                counts[cache_key] = 0
        except Exception:
            counts[cache_key] = 0

    return counts
