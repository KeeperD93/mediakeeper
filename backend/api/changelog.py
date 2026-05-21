"""
Changelog API — parse CHANGELOG.md and track the version the user has seen.

The `/combined` sub-routes merge this admin changelog with the Portal
changelog so the admin sees both surfaces in a single timeline + modal.
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
from api.auth import get_current_user
from api.portal_changelog import (
    PORTAL_VERSION,
    _parse_changelog as _parse_portal_changelog,
)

logger = logging.getLogger("mediakeeper.changelog")

router = APIRouter(prefix="/api/changelog", tags=["changelog"])

# ── Current version (single source of truth) ──
APP_VERSION = "0.9.9"

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
    model_config = ConfigDict(extra="forbid")

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


def _merge_changelogs(
    admin_versions: list[dict],
    portal_versions: list[dict],
) -> list[dict]:
    """Merge admin and portal changelogs into a single per-version timeline.

    Each returned entry preserves the version string and date, and exposes
    `admin` and `portal` sub-objects (either may be ``None`` when that
    surface has no entry for the version). The admin date wins on conflict;
    the portal date is used only when the version is portal-only.
    """
    by_version: dict[str, dict] = {}

    for v in admin_versions:
        ver = v["version"]
        by_version[ver] = {
            "version": ver,
            "date": v["date"],
            "admin": v["categories"],
            "portal": None,
        }

    for v in portal_versions:
        ver = v["version"]
        if ver in by_version:
            by_version[ver]["portal"] = v["categories"]
        else:
            by_version[ver] = {
                "version": ver,
                "date": v["date"],
                "admin": None,
                "portal": v["categories"],
            }

    return sorted(
        by_version.values(),
        key=lambda x: (x["date"], x["version"]),
        reverse=True,
    )


@router.get("/combined")
async def get_combined_changelog(
    limit: int = 0,
    lang: str = "fr",
    _: User = Depends(get_current_user),
):
    """Return the admin + portal changelogs merged by version.

    Each version entry exposes `admin` and `portal` sub-sections; either
    may be ``None`` if that surface has nothing for the version.
    """
    admin_versions = _parse_changelog(lang=lang, max_versions=0)
    portal_versions = _parse_portal_changelog(lang=lang, max_versions=0)
    merged = _merge_changelogs(admin_versions, portal_versions)
    if limit and limit > 0:
        merged = merged[:limit]
    return {
        "app_version": APP_VERSION,
        "portal_version": PORTAL_VERSION,
        "versions": merged,
    }


@router.get("/combined/check")
async def check_combined_new_versions(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Check whether the admin has seen both the admin AND portal versions."""
    from services.settings import get_user_preferences
    prefs = await get_user_preferences(db, user.id)
    prefs_data = json.loads(prefs.preferences) if prefs and prefs.preferences else {}

    admin_seen = prefs_data.get("changelog_seen_version", "")
    portal_seen = prefs_data.get("portal_changelog_seen_version", "")

    admin_has_new = admin_seen != APP_VERSION
    portal_has_new = portal_seen != PORTAL_VERSION

    return {
        "app_version": APP_VERSION,
        "portal_version": PORTAL_VERSION,
        "admin_seen": admin_seen,
        "portal_seen": portal_seen,
        "admin_has_new": admin_has_new,
        "portal_has_new": portal_has_new,
        "has_any_new": admin_has_new or portal_has_new,
    }


class MarkCombinedSeenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app_version: str = ""
    portal_version: str = ""


@router.post("/combined/seen")
async def mark_combined_seen(
    req: MarkCombinedSeenRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mark both the admin and portal versions as seen in a single call."""
    from services.settings import get_user_preferences, upsert_user_preferences
    prefs = await get_user_preferences(db, user.id)
    prefs_data = json.loads(prefs.preferences) if prefs and prefs.preferences else {}

    app_version = req.app_version or APP_VERSION
    portal_version = req.portal_version or PORTAL_VERSION

    prefs_data["changelog_seen_version"] = app_version
    prefs_data["portal_changelog_seen_version"] = portal_version

    await upsert_user_preferences(db, user.id, preferences=json.dumps(prefs_data))
    return {
        "success": True,
        "app_version": app_version,
        "portal_version": portal_version,
    }
