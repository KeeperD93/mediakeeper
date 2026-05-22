"""Path resolution & validation, management of external subtitle files."""
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from services.path_config import (
    get_existing_media_path_roots,
    is_path_within_backup_dir,
    validate_path_in_roots,
)
from ._constants import logger, _SUBTITLE_FILE_EXTENSIONS


async def _get_local_path_roots(db: AsyncSession | None) -> list[Path]:
    roots: list[Path] = []
    seen: set[str] = set()

    def _add_root(raw_path: str | Path | None):
        if not raw_path:
            return
        try:
            resolved = Path(raw_path).expanduser().resolve(strict=False)
        except (OSError, RuntimeError):
            return
        if not resolved.exists() or not resolved.is_dir():
            return
        # Refuse to resolve media files through the backup zone: a backup root
        # configured as a media path root, or a category accidentally pointing
        # at a backup directory, must not become a search base for media
        # resolution.
        if is_path_within_backup_dir(resolved):
            return
        key = str(resolved)
        if key in seen:
            return
        seen.add(key)
        roots.append(resolved)

    for root in get_existing_media_path_roots():
        _add_root(root)

    if db is not None:
        try:
            from services.media_manager import get_categories

            for category in await get_categories(db):
                _add_root(category.get("path"))
        except Exception as exc:
            logger.debug(f"[opensubtitles] Unable to read media categories: {exc}")

    for fallback in ["/media", "/mnt", "/data/media", "/volume1/medias"]:
        _add_root(fallback)

    return roots


async def _resolve_local_path(db: AsyncSession | None, emby_path: str) -> str:
    """Translate an Emby path to the local path accessible inside the container.

    Returns an empty string when no candidate inside the configured media
    roots matches the Emby path. Callers must treat ``""`` as a refusal
    and not feed it to downstream consumers (ffprobe, unlink…).
    """
    raw_path = (emby_path or "").strip()
    if not raw_path:
        return ""

    try:
        resolved_input = Path(raw_path).expanduser().resolve(strict=False)
    except (ValueError, OSError, RuntimeError):
        resolved_input = Path(raw_path)

    roots = await _get_local_path_roots(db)

    def _within_roots(candidate: Path) -> bool:
        return any(candidate == r or r in candidate.parents for r in roots)

    # Defence in depth: an Emby path that already exists at the same
    # absolute location inside this container is only trustworthy when
    # it sits under one of the configured media roots. Otherwise a
    # compromised Emby (or a shared mount tree) could feed arbitrary
    # readable files (``/etc/passwd``, ``/proc/*``, secrets in
    # ``/data``) to downstream consumers.
    if (
        resolved_input.exists()
        and not is_path_within_backup_dir(resolved_input)
        and _within_roots(resolved_input)
    ):
        return str(resolved_input)

    parts = Path(raw_path).parts
    for root in roots:
        for i in range(1, len(parts)):
            sub_path = Path(*parts[i:])
            candidate = (root / sub_path).resolve(strict=False)
            if not candidate.exists():
                continue
            # Defence in depth: even if the root passed the filter, refuse to
            # return a candidate that ended up inside the backup zone.
            if is_path_within_backup_dir(candidate):
                continue
            return str(candidate)

    logger.warning(f"[opensubtitles] Path not resolved locally: {emby_path}")
    return ""


def _empty_existing_payload(file_path: str = "", analysis_source: str = "none") -> dict:
    return {
        "streams": [],
        "audio_streams": [],
        "file_path": file_path,
        "analysis_source": analysis_source,
    }


def _normalize_path_validation_error(path_error: str) -> str:
    if path_error == "file_type_not_allowed":
        return "File type not allowed"
    return path_error


def suggest_subtitle_path(media_path: str, language: str) -> str:
    """Compute the subtitle path from the media file (Emby path).
    Example: movie.mkv -> movie.fr.srt
    The returned path must be visible inside the container via the Docker volumes."""
    p = Path(media_path)
    lang_short = {
        "fre": "fr", "eng": "en", "spa": "es", "ger": "de", "ita": "it", "por": "pt",
        "nld": "nl", "dut": "nl", "rus": "ru", "jpn": "ja", "chi": "zh", "kor": "ko",
        "ara": "ar", "pol": "pl", "tur": "tr", "swe": "sv", "dan": "da", "nor": "no",
        "fin": "fi", "ces": "cs", "ron": "ro", "hun": "hu", "ell": "el", "heb": "he",
        "tha": "th", "vie": "vi", "ind": "id", "ukr": "uk", "hin": "hi",
    }.get(language, language[:2] if len(language) >= 2 else language)
    return str(p.with_suffix(f".{lang_short}.srt"))


def delete_external_subtitle(filepath: str, allow_any_path: bool = False) -> dict:
    """Delete an external subtitle file from disk."""
    try:
        if allow_any_path:
            p = Path(filepath).expanduser().resolve(strict=False)
        else:
            p, path_error = validate_path_in_roots(
                filepath,
                allow_missing=False,
                must_be_dir=False,
                allowed_suffixes=_SUBTITLE_FILE_EXTENSIONS,
                label="Subtitle file",
            )
            if path_error:
                return {"error": _normalize_path_validation_error(path_error)}
        p.unlink()
        logger.info(f"[opensubtitles] Deleted subtitle: {p}")
        return {"success": True, "path": str(p)}
    except Exception as e:
        return {"error": str(e)[:200]}
