"""Subtitle search, download, and user quota."""
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from core.http_client import get_external_client
from services.path_config import validate_path_in_roots

from . import auth
from ._constants import logger, OS_API_BASE, _SUBTITLE_FILE_EXTENSIONS
from .hashing import compute_quality_score
from .paths import _normalize_path_validation_error

# A legitimate subtitle is a few hundred KB at most; cap the download so a
# malicious OpenSubtitles response or a redirect MITM cannot OOM the backend
# or fill the media volume by streaming gigabytes (#402).
MAX_SUBTITLE_BYTES = 16 * 1024 * 1024


async def search_subtitles(
    db: AsyncSession,
    query: str = "",
    imdb_id: str = "",
    tmdb_id: str = "",
    season: int = 0,
    episode: int = 0,
    languages: str = "fr,en",
    moviehash: str = "",
) -> dict:
    """Recherche de sous-titres via OpenSubtitles API."""
    headers = await auth._get_headers(db)
    if not headers:
        return {"error": "not_configured", "results": []}

    params = {}
    if moviehash:
        params["moviehash"] = moviehash
    if imdb_id:
        params["imdb_id"] = imdb_id.replace("tt", "")
    # Pour les episodes, le tmdb_id d'Emby est celui de l'episode, no la series
    # OpenSubtitles attend le tmdb_id de la series → use query + season/episode
    if tmdb_id and not (season and episode):
        params["tmdb_id"] = tmdb_id
    if query:
        params["query"] = query
    if languages:
        params["languages"] = languages
    if season and season > 0:
        params["season_number"] = season
    if episode and episode > 0:
        params["episode_number"] = episode

    params["order_by"] = "download_count"
    params["order_direction"] = "desc"

    try:
        client = get_external_client()
        res = await client.get(
            f"{OS_API_BASE}/subtitles",
            params=params,
            headers=headers,
            timeout=15.0,
        )

        if res.status_code != 200:
            logger.warning("[opensubtitles] Search failed: %s", res.status_code)
            return {"error": f"api_error_{res.status_code}", "results": []}

        data = res.json()
        results = []
        for item in data.get("data", []):
            attrs = item.get("attributes", {})
            files = attrs.get("files", [])
            feature = attrs.get("feature_details", {})

            hash_match = bool(moviehash and attrs.get("moviehash_match", False))

            for f in files:
                entry = {
                    "file_id": f.get("file_id"),
                    "file_name": f.get("file_name", ""),
                    "language": attrs.get("language", ""),
                    "download_count": attrs.get("download_count", 0),
                    "hearing_impaired": attrs.get("hearing_impaired", False),
                    "foreign_parts_only": attrs.get("foreign_parts_only", False),
                    "ai_translated": attrs.get("ai_translated", False),
                    "machine_translated": attrs.get("machine_translated", False),
                    "ratings": attrs.get("ratings", 0),
                    "from_trusted": attrs.get("from_trusted", False),
                    "upload_date": attrs.get("upload_date", ""),
                    "feature_title": feature.get("title", ""),
                    "feature_year": feature.get("year"),
                    "subtitle_id": item.get("id"),
                    "hash_match": hash_match,
                }
                entry["quality_score"] = compute_quality_score(entry, hash_match)
                results.append(entry)

        results.sort(key=lambda r: r.get("quality_score", 0), reverse=True)

        return {
            "results": results,
            "total": data.get("total_count", len(results)),
        }

    except Exception:
        logger.exception("[opensubtitles] Search failed")
        return {"error": "search_failed", "results": []}


async def download_subtitle(
    db: AsyncSession,
    file_id: int,
    destination_path: str,
    media_duration_sec: float = 0,
    allow_any_path: bool = False,
) -> dict:
    """Download a subtitle and write it to disk.
    If media_duration_sec > 0, check sync after writing.
    Automatically converts encoding to UTF-8 if needed.
    """
    headers = await auth._get_headers(db)
    if not headers:
        return {"error": "not_configured"}

    try:
        if allow_any_path:
            dest = Path(destination_path).expanduser().resolve(strict=False)
        else:
            dest, path_error = validate_path_in_roots(
                destination_path,
                allow_missing=True,
                must_be_dir=False,
                allowed_suffixes=_SUBTITLE_FILE_EXTENSIONS,
                label="Subtitle file",
            )
            if path_error:
                return {"error": _normalize_path_validation_error(path_error)}

        client = get_external_client()

        res = await client.post(
            f"{OS_API_BASE}/download",
            json={"file_id": file_id},
            headers=headers,
            timeout=15.0,
        )

        if res.status_code != 200:
            return {"error": f"download_request_failed_{res.status_code}"}

        data = res.json()
        download_link = data.get("link")
        remaining = data.get("remaining", 0)
        reset_time = data.get("reset_time", "")

        if not download_link:
            return {"error": "no_download_link"}

        content = bytearray()
        async with client.stream(
            "GET", download_link, timeout=30.0, follow_redirects=True,
        ) as sub_res:
            if sub_res.status_code != 200:
                return {"error": f"download_failed_{sub_res.status_code}"}
            async for chunk in sub_res.aiter_bytes():
                content.extend(chunk)
                if len(content) > MAX_SUBTITLE_BYTES:
                    return {"error": "subtitle_too_large"}

        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(bytes(content))

        logger.info("[opensubtitles] Downloaded subtitle → %s", dest)

        result = {
            "success": True,
            "path": str(dest),
            "size": len(sub_res.content),
            "remaining": remaining,
            "reset_time": reset_time,
        }

        try:
            from services.subtitle_tools import fix_encoding
            enc_result = fix_encoding(str(dest), allow_any_path=allow_any_path)
            result["encoding"] = enc_result
        except Exception as e:
            logger.warning("[opensubtitles] Encoding fix error: %s", e)

        if media_duration_sec > 0:
            try:
                from services.subtitle_tools import check_desync
                desync = check_desync(str(dest), media_duration_sec, allow_any_path=allow_any_path)
                result["desync"] = desync
                if desync.get("desynced"):
                    logger.warning(
                        f"[opensubtitles] Desync detected for {dest}: "
                        f"delta={desync['delta_sec']}s"
                    )
            except Exception as e:
                logger.warning("[opensubtitles] Desync check error: %s", e)

        return result

    except Exception:
        logger.exception("[opensubtitles] Download failed")
        return {"error": "download_failed"}


async def get_quota(db: AsyncSession) -> dict:
    """Return quota info (remaining downloads)."""
    headers = await auth._get_headers(db)
    if not headers:
        return {"error": "not_configured"}

    try:
        client = get_external_client()
        res = await client.get(
            f"{OS_API_BASE}/infos/user",
            headers=headers,
            timeout=10.0,
        )
        if res.status_code == 200:
            data = res.json().get("data", {})
            return {
                "remaining_downloads": data.get("remaining_downloads", 0),
                "allowed_downloads": data.get("allowed_downloads", 0),
                "level": data.get("level", ""),
                "vip": data.get("vip", False),
                "reset_time": data.get("reset_time", ""),
            }
        return {"error": f"api_error_{res.status_code}"}
    except Exception:
        logger.exception("[opensubtitles] Quota failed")
        return {"error": "quota_failed"}
