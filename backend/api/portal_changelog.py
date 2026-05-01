"""Portal changelog API — parse CHANGELOG_PORTAL_*.md and track the
version the viewer has seen.

Distinct from the admin changelog so that the public Portal surface shows
only viewer-facing changes, with its own version line that drifts from the
admin APP_VERSION. Authenticates via the Portal-scoped ``rq_token`` cookie.
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
from api.portal.deps import get_portal_user

logger = logging.getLogger("mediakeeper.portal_changelog")

router = APIRouter(prefix="/api/portal/changelog", tags=["portal-changelog"])

# Current Portal viewer version. Bumped independently of APP_VERSION.
PORTAL_VERSION = "0.2.0"

_BASE_DIR = Path(__file__).resolve().parent.parent
_ALT_DIRS = [Path("/app/backend"), Path("/app"), _BASE_DIR.parent]


def _find_changelog(lang: str = "fr") -> Path | None:
    """Locate the Portal changelog file for the given language."""
    filename = f"CHANGELOG_PORTAL_{lang.upper()}.md"
    fallback = "CHANGELOG_PORTAL.md"

    for base in [_BASE_DIR] + _ALT_DIRS:
        candidate = base / filename
        if candidate.exists():
            return candidate

    for base in [_BASE_DIR] + _ALT_DIRS:
        candidate = base / fallback
        if candidate.exists():
            return candidate

    return None


def _parse_changelog(lang: str = "fr", max_versions: int = 0) -> list[dict]:
    """Parse CHANGELOG_PORTAL_XX.md into a list of structured versions."""
    path = _find_changelog(lang)
    if not path:
        logger.warning(f"[PORTAL_CHANGELOG] No changelog file found for lang={lang}")
        return []

    logger.debug(f"[PORTAL_CHANGELOG] Using: {path}")
    text = path.read_text(encoding="utf-8")
    versions = []
    current_version = None
    current_category = None

    for line in text.splitlines():
        # ## [0.1.0] - 2026-04-19
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
async def get_portal_changelog(
    limit: int = 0,
    lang: str = "fr",
    _: User = Depends(get_portal_user),
):
    """Return the parsed Portal changelog in the requested language."""
    return {
        "current_version": PORTAL_VERSION,
        "versions": _parse_changelog(lang=lang, max_versions=limit),
    }


@router.get("/current")
async def get_current_portal_version():
    """Return the current Portal viewer version (no auth required)."""
    return {"version": PORTAL_VERSION}


@router.get("/check")
async def check_new_portal_version(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_portal_user),
):
    """Check whether the user has seen the current Portal viewer version."""
    from services.settings import get_user_preferences
    prefs = await get_user_preferences(db, user.id)
    prefs_data = json.loads(prefs.preferences) if prefs and prefs.preferences else {}
    seen_version = prefs_data.get("portal_changelog_seen_version", "")
    return {
        "current_version": PORTAL_VERSION,
        "seen_version": seen_version,
        "has_new": seen_version != PORTAL_VERSION,
    }


class MarkSeenRequest(BaseModel):
    version: str = ""


@router.post("/seen")
async def mark_portal_changelog_seen(
    req: MarkSeenRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_portal_user),
):
    """Mark the Portal viewer version as seen by the user."""
    version = req.version or PORTAL_VERSION
    from services.settings import get_user_preferences, upsert_user_preferences
    prefs = await get_user_preferences(db, user.id)
    prefs_data = json.loads(prefs.preferences) if prefs and prefs.preferences else {}
    prefs_data["portal_changelog_seen_version"] = version
    await upsert_user_preferences(db, user.id, preferences=json.dumps(prefs_data))
    return {"success": True, "version": version}
