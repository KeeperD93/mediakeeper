"""
Onboarding API — first-run configuration wizard.
"""
import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from api.auth import get_current_user, resolve_valid_admin_session
from models.user import User
from constants.tools import TOOL_EMBY, TOOL_TMDB
from services.settings import get_setting, set_setting, get_tools_config
from services.media_manager import get_categories

logger = logging.getLogger("mediakeeper.onboarding")
router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])

ONBOARDING_KEY = "setup.onboarding_done"


# ── Status ────────────────────────────────────────────────────────────────────

@router.get("/status")
async def get_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Return the onboarding status.
    Accessible without full auth (just a valid JWT) so the wizard can render
    before everything is configured.
    """
    # Light auth: the wizard must render before everything is configured, so we
    # accept a plain valid admin session. resolve_valid_admin_session runs the
    # live checks minus the must-change-password gate (the bootstrap admin still
    # has the seed password pending). Any failure maps to authenticated:false.
    if await resolve_valid_admin_session(request, db) is None:
        return {"authenticated": False}

    done = await get_setting(db, ONBOARDING_KEY)
    config = await get_tools_config(db)

    emby_cfg = config.get(TOOL_EMBY, {})
    tmdb_cfg = config.get(TOOL_TMDB, {})

    return {
        "authenticated":    True,
        "onboarding_done":  done == "true",
        "steps": {
            TOOL_EMBY: bool(emby_cfg.get("url") and emby_cfg.get("api_key")),
            TOOL_TMDB: bool(tmdb_cfg.get("api_key")),
            "folders": await _check_folders_configured(db),
        },
    }


async def _check_folders_configured(db: AsyncSession) -> bool:
    """Check whether at least one media folder is configured via DB or env."""
    categories = await get_categories(db)
    if any((c.get("path") or "").strip() for c in categories):
        return True

    import os
    return bool(
        os.getenv("MEDIAKEEPER_PATH_ROOTS")
        or os.getenv("MEDIA_TELECHARGEMENT")
        or os.getenv("MEDIA_FILMS")
        or os.getenv("MEDIA_SERIES")
    )


# ── Complete ──────────────────────────────────────────────────────────────────

@router.post("/complete")
async def complete_onboarding(
    db: AsyncSession = Depends(get_db),
    _:  User         = Depends(get_current_user),
):
    """Mark onboarding as completed.

    Folders are optional at this stage: the operator can declare them
    later via Settings → Folders. The previous strict guard locked
    fresh installs that pulled the GHCR image without bind-mounting a
    host media directory yet — ``docker-compose.prod.yml`` ships with
    every media volume commented out by default, and forcing folders
    here turned an expected post-pull configuration step into a hard
    dead-end at the end of the wizard.
    """
    await set_setting(db, ONBOARDING_KEY, "true")
    logger.info("[ONBOARDING] Onboarding marked as completed")
    return {"success": True}


@router.post("/reset")
async def reset_onboarding(
    db: AsyncSession = Depends(get_db),
    _:  User         = Depends(get_current_user),
):
    """Reset onboarding (admin only)."""
    await set_setting(db, ONBOARDING_KEY, "false")
    return {"success": True}
