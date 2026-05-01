"""
Changelog API — parse CHANGELOG.md and track the version the user has seen.
"""
import re
import json
import logging
from pathlib import Path
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from models.user import User
from api.auth import get_current_user

logger = logging.getLogger("mediakeeper.changelog")

router = APIRouter(prefix="/api/changelog", tags=["changelog"])

# ── Current version (single source of truth) ──
APP_VERSION = "0.9.8"

# ── Path des files CHANGELOG ──
_BASE_DIR = Path(__file__).resolve().parent.parent
_ALT_DIRS = [Path("/app/backend"), Path("/app"), _BASE_DIR.parent]


def _find_changelog(lang: str = "fr") -> Path | None:
    """Find the CHANGELOG file for the given language."""
    filename = f"CHANGELOG_{lang.upper()}.md"
    fallback = "CHANGELOG.md"

    for base in [_BASE_DIR] + _ALT_DIRS:
        candidate = base / filename
        if candidate.exists():
            return candidate

    # Fallback to generic CHANGELOG.md
    for base in [_BASE_DIR] + _ALT_DIRS:
        candidate = base / fallback
        if candidate.exists():
            return candidate

    return None


def _parse_changelog(lang: str = "fr", max_versions: int = 0) -> list[dict]:
    """Parse CHANGELOG_XX.md -> a list of structured versions."""
    path = _find_changelog(lang)
    if not path:
        logger.warning(f"[CHANGELOG] No changelog file found for lang={lang}")
        return []

    logger.debug(f"[CHANGELOG] Using: {path}")
    text = path.read_text(encoding="utf-8")
    versions = []
    current_version = None
    current_category = None

    for line in text.splitlines():
        # ## [0.9.1] - 2026-03-28
        m = re.match(r"^## \[([^\]]+)\]\s*-\s*(.+)$", line)
        if m:
            if current_version:
                versions.append(current_version)
                if max_versions and len(versions) >= max_versions:
                    return versions
            current_version = {
                "version": m.group(1).strip(),
                "date": m.group(2).strip(),
                "categories": {},
            }
            current_category = None
            continue

        # ### Added / Fixed / Changed / Removed
        m = re.match(r"^### (.+)$", line)
        if m and current_version is not None:
            current_category = m.group(1).strip()
            current_version["categories"][current_category] = []
            continue

        # - Item
        m = re.match(r"^- (.+)$", line)
        if m and current_version is not None and current_category:
            current_version["categories"][current_category].append(m.group(1).strip())

    if current_version:
        versions.append(current_version)

    return versions


@router.get("/")
async def get_changelog(
    limit: int = 0,
    lang: str = "fr",
    _: User = Depends(get_current_user),
):
    """Return the parsed changelog in the requested language."""
    return {
        "current_version": APP_VERSION,
        "versions": _parse_changelog(lang=lang, max_versions=limit),
    }


@router.get("/current")
async def get_current_version():
    """Return la version current (pas besoin d'auth)."""
    return {"version": APP_VERSION}


@router.get("/check")
async def check_new_version(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Check whether the user has seen the current version."""
    from services.settings import get_user_preferences
    prefs = await get_user_preferences(db, user.id)
    prefs_data = json.loads(prefs.preferences) if prefs and prefs.preferences else {}
    seen_version = prefs_data.get("changelog_seen_version", "")
    return {
        "current_version": APP_VERSION,
        "seen_version": seen_version,
        "has_new": seen_version != APP_VERSION,
    }


class MarkSeenRequest(BaseModel):
    version: str = ""


@router.post("/seen")
async def mark_changelog_seen(
    req: MarkSeenRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Marque la version comme vue par l'user."""
    version = req.version or APP_VERSION
    from services.settings import get_user_preferences, upsert_user_preferences
    prefs = await get_user_preferences(db, user.id)
    prefs_data = json.loads(prefs.preferences) if prefs and prefs.preferences else {}
    prefs_data["changelog_seen_version"] = version
    await upsert_user_preferences(db, user.id, preferences=json.dumps(prefs_data))
    return {"success": True, "version": version}
