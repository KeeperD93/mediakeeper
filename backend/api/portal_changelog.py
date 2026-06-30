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
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from models.user import User
from models.portal.profile import UserProfile
from api.portal.deps import get_current_profile

logger = logging.getLogger("mediakeeper.portal_changelog")

router = APIRouter(prefix="/api/portal/changelog", tags=["portal-changelog"])

# Current Portal viewer version. Aligned with APP_VERSION at the 1.0.0
# launch; the two trackers may drift again later if the surfaces have
# independent release cadences.
PORTAL_VERSION = "1.0.0-rc.5"

_BASE_DIR = Path(__file__).resolve().parent.parent
_ALT_DIRS = [Path("/app/backend"), Path("/app"), _BASE_DIR.parent]

# Languages with a shipped CHANGELOG file. Any other value is coerced to "fr"
# so an untrusted query string can never be interpolated into the filename.
_SUPPORTED_LANGS = frozenset({"fr", "en"})


def _find_changelog(lang: str = "fr") -> Path | None:
    """Locate the Portal changelog file for the given language."""
    if lang.lower() not in _SUPPORTED_LANGS:
        lang = "fr"
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


def _has_entries(version: dict) -> bool:
    """True when a version carries at least one non-empty category. Versions
    that shipped only changes on the other surface (admin vs portal) parse to
    empty categories and must be skipped so they don't render as blank cards."""
    return any(version["categories"].values())


def _parse_changelog(lang: str = "fr", max_versions: int = 0) -> list[dict]:
    """Parse CHANGELOG_PORTAL_XX.md into a list of structured versions."""
    path = _find_changelog(lang)
    if not path:
        logger.warning("[PORTAL_CHANGELOG] No changelog file found for lang=%s", lang)
        return []

    logger.debug("[PORTAL_CHANGELOG] Using: %s", path)
    text = path.read_text(encoding="utf-8")
    versions = []
    current_version = None
    current_category = None

    for line in text.splitlines():
        # ## [0.1.0] - 2026-04-19
        m = re.match(r"^## \[([^\]]+)\]\s*-\s*(.+)$", line)
        if m:
            if current_version and _has_entries(current_version):
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

    if current_version and _has_entries(current_version):
        versions.append(current_version)

    return versions


@router.get("/")
async def get_portal_changelog(
    limit: int = 0,
    lang: str = "fr",
    up: tuple[User, UserProfile] = Depends(get_current_profile),
):
    """Return the parsed Portal changelog in the requested language."""
    return {
        "current_version": PORTAL_VERSION,
        "versions": _parse_changelog(lang=lang, max_versions=limit),
    }


@router.get("/current")
async def get_current_portal_version():
    """Return the current Portal viewer version.

    Public on purpose — exposes a version badge with no PII, intentionally
    unauthenticated so a marketing/landing surface can render it without
    a login round-trip.
    """
    return {"version": PORTAL_VERSION}


@router.get("/check")
async def check_new_portal_version(
    db: AsyncSession = Depends(get_db),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
):
    """Check whether the user has seen the current Portal viewer version."""
    from services.settings import get_user_preferences
    user, _ = up
    prefs = await get_user_preferences(db, user.id)
    prefs_data = json.loads(prefs.preferences) if prefs and prefs.preferences else {}
    seen_version = prefs_data.get("portal_changelog_seen_version", "")
    return {
        "current_version": PORTAL_VERSION,
        "seen_version": seen_version,
        "has_new": seen_version != PORTAL_VERSION,
    }


class MarkSeenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = ""


@router.post("/seen")
async def mark_portal_changelog_seen(
    req: MarkSeenRequest,
    db: AsyncSession = Depends(get_db),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
):
    """Mark the Portal viewer version as seen by the user."""
    user, _ = up
    version = req.version or PORTAL_VERSION
    from services.settings import get_user_preferences, upsert_user_preferences
    prefs = await get_user_preferences(db, user.id)
    prefs_data = json.loads(prefs.preferences) if prefs and prefs.preferences else {}
    prefs_data["portal_changelog_seen_version"] = version
    await upsert_user_preferences(db, user.id, preferences=json.dumps(prefs_data))
    return {"success": True, "version": version}
