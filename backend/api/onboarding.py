"""
Onboarding API — first-run configuration wizard.
"""
import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from api.auth import get_current_user, COOKIE_NAME
from core.security import (
    decode_access_token,
    is_backoffice_admin,
    is_token_valid_for_revocation_pivot,
)
from models.user import User
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
    # Light auth so the wizard can render before everything is configured,
    # but it mirrors get_current_user's live checks (active account, still a
    # backoffice admin, not force-logged-out) so a revoked/deactivated admin
    # token can't read setup state. The must-change-password gate is left out
    # on purpose: the bootstrap admin must reach the wizard with the seed
    # password still pending. Any failure maps to authenticated:false.
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return {"authenticated": False}
    payload = decode_access_token(token)
    if not payload or payload.get("scope") != "admin":
        return {"authenticated": False}
    username = payload.get("sub")
    if not username:
        return {"authenticated": False}
    user = (
        await db.execute(select(User).where(User.username == username))
    ).scalar_one_or_none()
    if (
        not user
        or not user.is_active
        or not is_backoffice_admin(user.username)
        or not is_token_valid_for_revocation_pivot(payload.get("iat"), user.tokens_invalidated_at)
    ):
        return {"authenticated": False}

    done = await get_setting(db, ONBOARDING_KEY)
    config = await get_tools_config(db)

    emby_cfg = config.get("emby", {})
    tmdb_cfg = config.get("tmdb", {})

    return {
        "authenticated":    True,
        "onboarding_done":  done == "true",
        "steps": {
            "emby":    bool(emby_cfg.get("url") and emby_cfg.get("api_key")),
            "tmdb":    bool(tmdb_cfg.get("api_key")),
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
