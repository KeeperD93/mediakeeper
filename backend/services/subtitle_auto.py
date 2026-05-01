"""
Auto-download de sous-titres for les new medias.

Verifie les items ajoutes in Emby from le last check,
et telecharge automatically les sous-titres according to le profil par defaut.
"""
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from services.settings import get_setting, set_setting
from services.subtitle_profiles import get_default_profile
from services.opensubtitles import (
    search_subtitles,
    download_subtitle,
    compute_file_hash,
    _normalize_lang,
)
from services.subtitle_history import record_download

logger = logging.getLogger("mediakeeper.subtitle_auto")

_IMAGE_CODECS = {"pgssub", "pgs", "vobsub", "dvdsub", "dvbsub", "hdmv_pgs_subtitle", "xsub"}


async def check_and_download_new(db: AsyncSession) -> None:
    """Verifie les new medias et telecharge les sous-titres missing."""
    from services.emby import _get_emby_config
    from core.http_client import get_internal_client

    # 1. Verifier le profil par defaut
    profile = await get_default_profile(db)
    if not profile or not profile.get("auto_download"):
        return

    languages = profile.get("languages") or ["fre", "eng"]
    min_score = profile.get("min_score", 3.0)

    # 2. Recuperer le last check
    last_check = await get_setting(db, "subtitle_auto.last_check")
    now = datetime.now(timezone.utc)

    if not last_check:
        # Premiere execution : ne pas scanner tout, juste marquer le timestamp
        await set_setting(db, "subtitle_auto.last_check", now.isoformat())
        logger.info("[subtitle_auto] First run, timestamp set. Will check new items next run.")
        return

    # 3. Recuperer les items ajoutes from last_check
    cfg = await _get_emby_config(db)
    if not cfg:
        return

    url, api_key = cfg
    headers = {"X-Emby-Token": api_key}
    client = get_internal_client()

    try:
        res = await client.get(f"{url}/Items", params={
            "MinDateCreated": last_check,
            "IncludeItemTypes": "Movie,Episode",
            "Recursive": "true",
            "Fields": "MediaSources,MediaStreams,Path,ProviderIds",
            "SortBy": "DateCreated",
            "SortOrder": "Descending",
            "Limit": "50",
        }, headers=headers, timeout=30.0)

        if res.status_code != 200:
            logger.warning(f"[subtitle_auto] Emby returned {res.status_code}")
            return

        data = res.json()
        items = data.get("Items", [])

        if not items:
            await set_setting(db, "subtitle_auto.last_check", now.isoformat())
            return

        logger.info(f"[subtitle_auto] Found {len(items)} new items since {last_check}")

        lang_map = {
            "fre": "fr", "eng": "en", "spa": "es", "ger": "de", "ita": "it", "por": "pt",
            "jpn": "ja", "chi": "zh", "kor": "ko", "rus": "ru", "ara": "ar", "nld": "nl",
            "dut": "nl", "pol": "pl", "tur": "tr", "swe": "sv", "dan": "da", "nor": "no",
            "fin": "fi", "ces": "cs", "cze": "cs", "ron": "ro", "rum": "ro", "hun": "hu",
            "ell": "el", "gre": "el", "heb": "he", "tha": "th", "vie": "vi", "ind": "id",
            "ukr": "uk", "hin": "hi",
        }
        downloaded = 0

        for item in items:
            sources = item.get("MediaSources") or []
            if not sources:
                continue

            # Verifier les sous-titres existants
            sub_langs = set()
            for s in sources[0].get("MediaStreams", []):
                if s.get("Type") == "Subtitle":
                    codec = (s.get("Codec") or "").lower()
                    if codec in _IMAGE_CODECS:
                        continue
                    lang = (s.get("Language") or "").strip()
                    if lang:
                        sub_langs.add(_normalize_lang(lang))

            # Quelles langues manquent ?
            missing = [lang for lang in languages if lang not in sub_langs]
            if not missing:
                continue

            # Rechercher et teleload for each langue missing
            file_path = sources[0].get("Path", "")
            providers = item.get("ProviderIds") or {}
            item_name = item.get("Name", "")
            item_type = item.get("Type", "")

            for lang in missing[:1]:  # Une langue a la fois pour limiter le quota
                search_body = {
                    "query": item.get("SeriesName") or item_name,
                    "languages": lang_map.get(lang, lang),
                }
                if item_type == "Movie":
                    if providers.get("Tmdb"):
                        search_body["tmdb_id"] = providers["Tmdb"]
                    if providers.get("Imdb"):
                        search_body["imdb_id"] = providers["Imdb"]
                elif item_type == "Episode":
                    if item.get("ParentIndexNumber"):
                        search_body["season"] = item["ParentIndexNumber"]
                    if item.get("IndexNumber"):
                        search_body["episode"] = item["IndexNumber"]

                if file_path:
                    fhash = compute_file_hash(file_path)
                    if fhash:
                        search_body["moviehash"] = fhash

                results = await search_subtitles(db, **search_body)
                candidates = results.get("results", [])

                # Filtrer according to profil
                if profile.get("exclude_ai"):
                    candidates = [r for r in candidates if not r.get("ai_translated")]
                if profile.get("exclude_machine"):
                    candidates = [r for r in candidates if not r.get("machine_translated")]

                if not candidates:
                    continue

                best = candidates[0]
                if best.get("quality_score", 0) < min_score:
                    continue

                # Destination
                if not file_path:
                    continue
                lang_short = lang_map.get(lang, lang)
                dot_idx = file_path.rfind(".")
                dest = (file_path[:dot_idx] + f".{lang_short}.srt") if dot_idx > 0 else (file_path + f".{lang_short}.srt")

                dl = await download_subtitle(db, best["file_id"], dest)
                if dl.get("success"):
                    downloaded += 1
                    try:
                        await record_download(
                            db,
                            emby_item_id=item.get("Id", ""),
                            media_name=item_name,
                            media_type=item_type,
                            series_name=item.get("SeriesName"),
                            season=item.get("ParentIndexNumber"),
                            episode=item.get("IndexNumber"),
                            os_file_id=best["file_id"],
                            os_subtitle_id=best.get("subtitle_id", ""),
                            file_name=best.get("file_name", ""),
                            language=lang_map.get(lang, lang),
                            destination=dest,
                            file_size=dl.get("size"),
                            quality_score=best.get("quality_score"),
                            hash_match=best.get("hash_match", False),
                            hearing_impaired=best.get("hearing_impaired", False),
                            from_trusted=best.get("from_trusted", False),
                            ai_translated=best.get("ai_translated", False),
                            source="auto",
                        )
                    except Exception as e:
                        logger.warning(f"[subtitle_auto] History error: {e}")

                    # Refresh Emby item
                    try:
                        await client.post(
                            f"{url}/Items/{item.get('Id')}/Refresh",
                            headers=headers, timeout=10.0,
                        )
                    except Exception:
                        pass

                    if dl.get("remaining", 1) <= 0:
                        logger.info("[subtitle_auto] Quota exhausted, stopping")
                        break

            import asyncio
            await asyncio.sleep(2)  # Rate limiting

        logger.info(f"[subtitle_auto] Downloaded {downloaded} subtitles")

    except Exception as e:
        logger.error(f"[subtitle_auto] Error: {e}")

    # Mettre a jour le timestamp
    await set_setting(db, "subtitle_auto.last_check", now.isoformat())
