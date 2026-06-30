"""
Service de teleloading batch de sous-titres.
"""
import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from services.opensubtitles import search_subtitles, download_subtitle
from services.subtitle_history import record_download

logger = logging.getLogger("mediakeeper.subtitle_batch")

# Etat du batch en cours (module-level)
_batch_state = {
    "running": False,
    "cancel": False,
    "current": 0,
    "total": 0,
    "label": "",
    "completed": [],
    "failed": [],
    "skipped": [],
}


def get_batch_progress() -> dict:
    return {**_batch_state}


def cancel_batch():
    _batch_state["cancel"] = True


async def batch_download(
    db: AsyncSession,
    items: list[dict],
    profile: dict,
) -> dict:
    """Telecharge le meilleur sous-titre for each item according to le profil.

    items: [{emby_item_id, file_path, media_name, type, imdb_id, tmdb_id,
             series_name, season, episode, series_imdb_id}, ...]
    profile: profil de sous-titres (languages, min_score, exclude_ai, etc.)

    Return: {completed: [...], failed: [...], skipped: [...]}
    """
    global _batch_state

    _batch_state = {
        "running": True,
        "cancel": False,
        "current": 0,
        "total": len(items),
        "label": "",
        "completed": [],
        "failed": [],
        "skipped": [],
    }

    languages = profile.get("languages") or ["fre", "eng"]
    # Convertir codes 3 lettres en 2 lettres for l'API
    lang_map = {"fre": "fr", "eng": "en", "spa": "es", "ger": "de", "ita": "it", "por": "pt", "jpn": "ja", "chi": "zh", "kor": "ko", "rus": "ru", "ara": "ar", "nld": "nl", "pol": "pl", "tur": "tr", "swe": "sv", "dan": "da", "nor": "no", "fin": "fi", "ron": "ro", "hun": "hu", "ell": "el", "heb": "he", "tha": "th", "vie": "vi", "ind": "id", "ukr": "uk", "hin": "hi", "ces": "cs"}
    lang_param = ",".join(lang_map.get(lang, lang) for lang in languages)
    min_score = profile.get("min_score", 3.0)

    for i, item in enumerate(items):
        if _batch_state["cancel"]:
            logger.info("[batch] Cancelled by user")
            break

        _batch_state["current"] = i + 1
        _batch_state["label"] = item.get("media_name", "")

        try:
            # Rechercher les sous-titres
            search_body = {
                "query": item.get("series_name") or item.get("media_name", ""),
                "languages": lang_param,
            }
            if item.get("type") == "Movie":
                if item.get("tmdb_id"):
                    search_body["tmdb_id"] = str(item["tmdb_id"])
                if item.get("imdb_id"):
                    search_body["imdb_id"] = item["imdb_id"]
            elif item.get("type") == "Episode":
                if item.get("series_imdb_id"):
                    search_body["imdb_id"] = item["series_imdb_id"]
                if item.get("season"):
                    search_body["season"] = item["season"]
                if item.get("episode"):
                    search_body["episode"] = item["episode"]
            if item.get("file_path"):
                from services.opensubtitles import compute_file_hash
                fhash = compute_file_hash(item["file_path"])
                if fhash:
                    search_body["moviehash"] = fhash

            results = await search_subtitles(db, **search_body)
            candidates = results.get("results", [])

            if not candidates:
                _batch_state["skipped"].append({
                    "item_id": item.get("emby_item_id", ""),
                    "media_name": item.get("media_name", ""),
                    "reason": "no_results",
                })
                continue

            # Filtrer according to profil
            filtered = candidates
            if profile.get("exclude_ai"):
                filtered = [r for r in filtered if not r.get("ai_translated")]
            if profile.get("exclude_machine"):
                filtered = [r for r in filtered if not r.get("machine_translated")]
            if not profile.get("include_hi", False):
                # Ne pas exclure HI si c'est tout ce qu'il y a
                non_hi = [r for r in filtered if not r.get("hearing_impaired")]
                if non_hi:
                    filtered = non_hi

            if not filtered:
                _batch_state["skipped"].append({
                    "item_id": item.get("emby_item_id", ""),
                    "media_name": item.get("media_name", ""),
                    "reason": "filtered_out",
                })
                continue

            # Prendre le meilleur score (deja trie par score in search_subtitles)
            best = filtered[0]
            if best.get("quality_score", 0) < min_score:
                _batch_state["skipped"].append({
                    "item_id": item.get("emby_item_id", ""),
                    "media_name": item.get("media_name", ""),
                    "reason": f"score_too_low ({best.get('quality_score', 0)})",
                })
                continue

            # Calculer le path de destination
            file_path = item.get("file_path", "")
            if not file_path:
                _batch_state["skipped"].append({
                    "item_id": item.get("emby_item_id", ""),
                    "media_name": item.get("media_name", ""),
                    "reason": "no_file_path",
                })
                continue

            lang = best.get("language", "fr")
            lang_short = lang_map.get(lang, lang)
            dot_idx = file_path.rfind(".")
            dest = (file_path[:dot_idx] + f".{lang_short}.srt") if dot_idx > 0 else (file_path + f".{lang_short}.srt")

            # Teleload
            dl = await download_subtitle(db, best["file_id"], dest)

            if dl.get("success"):
                _batch_state["completed"].append({
                    "item_id": item.get("emby_item_id", ""),
                    "media_name": item.get("media_name", ""),
                    "language": lang,
                    "file_name": best.get("file_name", ""),
                    "score": best.get("quality_score", 0),
                    "desync": dl.get("desync"),
                    "encoding": dl.get("encoding"),
                })

                # Save in l'history
                try:
                    await record_download(
                        db,
                        emby_item_id=item.get("emby_item_id", ""),
                        media_name=item.get("media_name", ""),
                        media_type=item.get("type", ""),
                        series_name=item.get("series_name"),
                        season=item.get("season"),
                        episode=item.get("episode"),
                        os_file_id=best["file_id"],
                        os_subtitle_id=best.get("subtitle_id", ""),
                        file_name=best.get("file_name", ""),
                        language=lang,
                        destination=dest,
                        file_size=dl.get("size"),
                        quality_score=best.get("quality_score"),
                        hash_match=best.get("hash_match", False),
                        hearing_impaired=best.get("hearing_impaired", False),
                        foreign_parts_only=best.get("foreign_parts_only", False),
                        from_trusted=best.get("from_trusted", False),
                        ai_translated=best.get("ai_translated", False),
                        source="opensubtitles",
                    )
                except Exception as e:
                    logger.warning("[batch] History record error: %s", e)

                # Verifier quota restant
                if dl.get("remaining", 1) <= 0:
                    logger.info("[batch] Quota exhausted, stopping")
                    _batch_state["skipped"].extend([
                        {"item_id": it.get("emby_item_id", ""), "media_name": it.get("media_name", ""), "reason": "quota_exhausted"}
                        for it in items[i + 1:]
                    ])
                    break
            else:
                _batch_state["failed"].append({
                    "item_id": item.get("emby_item_id", ""),
                    "media_name": item.get("media_name", ""),
                    "error": dl.get("error", "unknown"),
                })

        except Exception as e:
            logger.error("[batch] Error for %s: %s", item.get('media_name', ''), e)
            _batch_state["failed"].append({
                "item_id": item.get("emby_item_id", ""),
                "media_name": item.get("media_name", ""),
                "error": str(e)[:200],
            })

        # Rate limiting : 1.5s entre each teleloading
        await asyncio.sleep(1.5)

    _batch_state["running"] = False
    _batch_state["label"] = ""

    logger.info(
        "[batch] Complete: %s OK, %s failed, %s skipped",
        len(_batch_state['completed']),
        len(_batch_state['failed']),
        len(_batch_state['skipped']),
    )

    return {
        "completed": _batch_state["completed"],
        "failed": _batch_state["failed"],
        "skipped": _batch_state["skipped"],
    }
