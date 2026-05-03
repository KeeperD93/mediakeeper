"""Custom avatar upload service for portal user profiles.

Files are written under ``/data/avatars/<user_id>_<timestamp>.<ext>`` so a
single user can only ever own one avatar at a time (older one is removed
on replace) and HTTP cache busts naturally because the filename changes.

The file is served back through ``GET /api/portal/avatars/{filename}``
(see ``api/portal/profile_settings.py``). We deliberately do NOT mount
the directory as a ``StaticFiles`` route — the explicit endpoint lets us
enforce content-type whitelisting, stream with cache headers, and refuse
path traversal in one place.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Final

from fastapi import HTTPException, UploadFile

from services.portal import strip_tags_and_trim  # noqa: F401  (kept for future hooks)
from services.path_config import DATA_ROOT


logger = logging.getLogger("mediakeeper.portal.avatars")

AVATAR_DIR: Final[Path] = DATA_ROOT / "avatars"

ALLOWED_EXTENSIONS: Final[set[str]] = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_MIME_TYPES: Final[set[str]] = {
    "image/jpeg", "image/png", "image/webp", "image/gif",
}
MAX_AVATAR_BYTES: Final[int] = 5 * 1024 * 1024  # 5 MB
UPLOAD_CHUNK_SIZE: Final[int] = 256 * 1024
HEADER_BYTES: Final[int] = 16


def _ensure_dir() -> None:
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)


def _safe_filename(filename: str) -> str:
    """Reject any path traversal attempt; return the basename only."""
    name = Path(filename or "").name
    if not name or name.startswith("."):
        raise HTTPException(status_code=400, detail="invalid_filename")
    return name


def avatar_path_for(filename: str) -> Path:
    """Resolve a stored filename to its absolute path, enforcing containment."""
    safe = _safe_filename(filename)
    target = (AVATAR_DIR / safe).resolve(strict=False)
    try:
        target.relative_to(AVATAR_DIR.resolve(strict=False))
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid_filename")
    return target


def _detected_image_extension(header: bytes) -> str | None:
    if header.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if header.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    if len(header) >= 12 and header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return ".webp"
    return None


def _extension_matches_detected(raw_ext: str, detected_ext: str | None) -> bool:
    if detected_ext is None:
        return False
    if raw_ext in {".jpg", ".jpeg"}:
        return detected_ext == ".jpg"
    return raw_ext == detected_ext


async def save_avatar(user_id: int, file: UploadFile) -> str:
    """Persist the uploaded image and return the stored filename.

    Caller is responsible for clearing any previous ``avatar_custom_path``
    on the profile (or calling :func:`delete_avatar` to remove the file).
    """
    _ensure_dir()

    raw_ext = Path(file.filename or "").suffix.lower()
    if raw_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="avatar_extension_not_allowed")

    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="avatar_mime_not_allowed")

    stored_name = f"{user_id}_{int(time.time() * 1000)}{raw_ext}"
    target = AVATAR_DIR / stored_name

    total = 0
    header = bytearray()
    try:
        with target.open("wb") as handle:
            while True:
                chunk = await file.read(UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                if len(header) < HEADER_BYTES:
                    header.extend(chunk[: HEADER_BYTES - len(header)])
                total += len(chunk)
                if total > MAX_AVATAR_BYTES:
                    raise HTTPException(status_code=413, detail="avatar_too_large")
                handle.write(chunk)
    except HTTPException:
        if target.exists():
            target.unlink()
        raise
    except Exception as exc:
        if target.exists():
            target.unlink()
        logger.error("[AVATAR] write failed user_id=%s: %s", user_id, exc)
        raise HTTPException(status_code=500, detail="avatar_write_failed") from exc

    if total == 0:
        target.unlink()
        raise HTTPException(status_code=400, detail="avatar_empty")

    detected_ext = _detected_image_extension(bytes(header))
    if not _extension_matches_detected(raw_ext, detected_ext):
        target.unlink()
        raise HTTPException(status_code=400, detail="avatar_invalid_image")

    logger.info("[AVATAR] saved user_id=%s name=%s size=%d", user_id, stored_name, total)
    return stored_name


def delete_avatar(stored_name: str | None) -> None:
    """Best-effort delete; missing file is not an error."""
    if not stored_name:
        return
    try:
        target = avatar_path_for(stored_name)
    except HTTPException:
        return
    if target.exists():
        try:
            target.unlink()
        except OSError as exc:
            logger.warning("[AVATAR] delete failed name=%s: %s", stored_name, exc)


def avatar_public_url(stored_name: str | None) -> str | None:
    """Build the public URL the frontend uses to fetch the avatar."""
    if not stored_name:
        return None
    return f"/api/portal/avatars/{stored_name}"
