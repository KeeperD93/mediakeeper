"""
Audit full de la bibliotheque : sous-titres missing, forced, image-only, encodage.
"""
import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_internal_client
from services.opensubtitles import _normalize_lang

logger = logging.getLogger("mediakeeper.subtitle_audit")

_IMAGE_CODECS = {"pgssub", "pgs", "vobsub", "dvdsub", "dvbsub", "hdmv_pgs_subtitle", "xsub"}

# Etat de l'audit en cours
_audit_state = {
    "running": False,
    "current": 0,
    "total": 0,
    "label": "",
}


def get_audit_progress() -> dict:
    return {**_audit_state}


async def run_audit(
    db: AsyncSession,
    languages: list[str] = None,
    library: str = "",
    checks: list[str] = None,
) -> dict:
    """Scanne toute la bibliotheque Emby et rapporte les problemes de sous-titres.

    checks: ["missing", "forced", "image_only", "encoding"]
    """
    global _audit_state
    from services.emby import _get_emby_config

    if languages is None:
        from services.subtitle_profiles import get_default_profile_languages
        languages = await get_default_profile_languages(db) or ["fre", "eng"]
    languages = [_normalize_lang(lang) for lang in languages if lang.strip()]

    if checks is None:
        checks = ["missing", "forced", "image_only"]

    cfg = await _get_emby_config(db)
    if not cfg:
        return {"error": "emby_not_configured"}

    url, api_key = cfg
    headers = {"X-Emby-Token": api_key}
    client = get_internal_client()

    _audit_state = {"running": True, "current": 0, "total": 0, "label": "Counting items..."}

    try:
        # Compter les items
        count_res = await client.get(f"{url}/Items", params={
            "IncludeItemTypes": "Movie,Episode",
            "Recursive": "true",
            "Limit": 0,
        }, headers=headers, timeout=15.0)
        total = count_res.json().get("TotalRecordCount", 0) if count_res.status_code == 200 else 0

        if total == 0:
            _audit_state["running"] = False
            return {"summary": {}, "items": []}

        _audit_state["total"] = total

        results = []
        summary = {
            "total_items": total,
            "missing": {},      # {lang: count}
            "image_only": 0,
            "missing_forced": 0,
            "encoding_issues": 0,
        }
        for lang in languages:
            summary["missing"][lang] = 0

        batch_size = 100
        for offset in range(0, total, batch_size):
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
                continue

            items = res.json().get("Items", [])

            for item in items:
                _audit_state["current"] += 1
                _audit_state["label"] = item.get("Name", "")

                sources = item.get("MediaSources") or []
                if not sources:
                    continue

                streams = sources[0].get("MediaStreams") or []
                file_path = sources[0].get("Path", "")

                # Analyser les streams
                text_sub_langs = set()
                image_sub_langs = set()
                audio_langs = set()
                has_any_text_sub = False
                external_srt_paths = []

                for s in streams:
                    if s.get("Type") == "Audio":
                        lang = (s.get("Language") or "").strip()
                        if lang:
                            audio_langs.add(_normalize_lang(lang))

                    elif s.get("Type") == "Subtitle":
                        codec = (s.get("Codec") or "").lower()
                        lang = (s.get("Language") or "").strip()
                        norm_lang = _normalize_lang(lang) if lang else ""

                        if codec in _IMAGE_CODECS:
                            if norm_lang:
                                image_sub_langs.add(norm_lang)
                        else:
                            has_any_text_sub = True
                            if norm_lang:
                                text_sub_langs.add(norm_lang)

                        # Collecter les files SRT externes for check encodage
                        if s.get("IsExternal") and s.get("Path"):
                            ext = Path(s["Path"]).suffix.lower()
                            if ext in (".srt", ".ass", ".ssa", ".vtt"):
                                external_srt_paths.append(s["Path"])

                issues = []

                # Check: sous-titres missing par langue
                if "missing" in checks:
                    for lang in languages:
                        if lang not in text_sub_langs:
                            issues.append(f"missing_{lang}")
                            summary["missing"][lang] += 1

                # Check: image-only (a des sous-titres but all en PGS/VOBSUB)
                if "image_only" in checks:
                    if image_sub_langs and not has_any_text_sub:
                        issues.append("image_only")
                        summary["image_only"] += 1

                # Check: forced missing (audio non principale without forced sub)
                if "forced" in checks:
                    # Si l'audio principale n'est pas in les langues demandees
                    # et qu'il n'y a no sous-titre forced
                    has_forced = any(
                        s.get("Type") == "Subtitle" and s.get("IsForced")
                        for s in streams
                    )
                    if audio_langs and not audio_langs.intersection(set(languages)) and not has_forced:
                        issues.append("missing_forced")
                        summary["missing_forced"] += 1

                # Check: encodage (files SRT externes non-UTF8)
                if "encoding" in checks:
                    for srt_path in external_srt_paths:
                        try:
                            import chardet
                            raw = Path(srt_path).read_bytes()[:4096]
                            detected = chardet.detect(raw)
                            enc = (detected.get("encoding") or "utf-8").upper()
                            if enc not in ("UTF-8", "ASCII", "UTF-8-SIG"):
                                issues.append(f"encoding:{enc}")
                                summary["encoding_issues"] += 1
                        except Exception:  # noqa: S110 -- intentional best-effort fallback, silently degrades to default behaviour
                            pass

                if issues:
                    if library:
                        lib_name = item.get("LibraryName") or ""
                        if lib_name and lib_name != library:
                            continue

                    results.append({
                        "item_id": item.get("Id", ""),
                        "name": item.get("Name", ""),
                        "type": item.get("Type", ""),
                        "series_name": item.get("SeriesName"),
                        "file_path": file_path,
                        "issues": issues,
                    })

    except Exception as e:
        logger.error(f"[audit] Error: {e}")
        _audit_state["running"] = False
        return {"error": str(e)[:200]}

    _audit_state["running"] = False
    _audit_state["label"] = ""

    logger.info(f"[audit] Complete: {len(results)} items with issues out of {total}")

    return {
        "summary": summary,
        "items": results,
    }
