"""GDPR opt-in user-facing endpoints.

All routes here are gated by the ``gdpr.enabled`` setting (default
``false``). When the toggle is off, the endpoints answer 404 with a
neutral ``{"detail": "Not found"}`` body so anonymous probes can't
infer that the GDPR plumbing exists at all.

Mounted under ``/api/portal``:

* ``GET    /me/export``           — ZIP archive of every user-bound row
* ``GET    /me/privacy-text``     — privacy policy HTML for the user's locale
* ``POST   /me/deletion-request`` — schedule grace-period deletion
* ``DELETE /me/deletion-request`` — cancel an active request
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.portal.deps import get_current_profile
from core.database import get_db
from core.rate_limit import limiter, portal_user_or_ip_key
from models.portal.profile import UserProfile
from models.user import User
from services.portal.gdpr import (
    GDPR_DPO_KEY,
    GDPR_PRIVACY_EN_KEY,
    GDPR_PRIVACY_FR_KEY,
    build_export_zip,
    cancel_deletion_request,
    get_purge_delay_days,
    is_gdpr_enabled,
    submit_deletion_request,
)
from services.settings import get_settings_map


router = APIRouter(prefix="/me", tags=["portal-gdpr"])
logger = logging.getLogger("mediakeeper.portal.gdpr")


def _not_found() -> HTTPException:
    """Neutral 404 used whenever the GDPR mode is disabled.

    A 403 would tell a probe the endpoint exists; 404 leaks nothing.
    """
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Not found",
    )


# ─────────────────────────── Export ───────────────────────────


@router.get("/export")
@limiter.limit("1/hour", key_func=portal_user_or_ip_key)
async def export_my_data(
    request: Request,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Return a ZIP archive of every row stored about the current user.

    Rate-limited to one call per hour per portal account: building the
    archive walks 12 tables and a malicious or buggy client should not
    be able to flood the worker.
    """
    if not await is_gdpr_enabled(db):
        raise _not_found()

    user, profile = up
    try:
        data, filename = await build_export_zip(db, user, profile)
    except OverflowError:
        logger.warning(
            "[GDPR] export bytes over cap for user_id=%s — answered 413",
            user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="export_too_large",
        )

    return Response(
        content=data,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(data)),
        },
    )


# ─────────────────────────── Deletion request ───────────────────────────


@router.post("/deletion-request")
async def post_deletion_request(
    request: Request,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Schedule a delayed account deletion.

    Idempotent: if the user already has a pending request, the call
    returns 409 with the existing schedule so the frontend can render
    the grace banner without a second submit.
    """
    if not await is_gdpr_enabled(db):
        raise _not_found()

    user, _ = up
    delay_days = await get_purge_delay_days(db)
    result = await submit_deletion_request(db, user, delay_days=delay_days)

    if result.get("status") == "already_pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "already_pending",
                "deletion_requested_at": result.get("deletion_requested_at"),
                "pending_deletion_at": result.get("pending_deletion_at"),
            },
        )
    return {
        "status": result["status"],
        "deletion_requested_at": result["deletion_requested_at"],
        "pending_deletion_at": result["pending_deletion_at"],
    }


@router.delete("/deletion-request")
async def delete_deletion_request(
    request: Request,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Cancel an active deletion request.

    Returns 200 on success, 404 when no request is pending — the user
    has nothing to cancel.
    """
    if not await is_gdpr_enabled(db):
        raise _not_found()

    user, _ = up
    cancelled = await cancel_deletion_request(db, user)
    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="no_pending_request",
        )
    return {"status": "cancelled"}


# ─────────────────────────── Privacy text ───────────────────────────


_VALID_LANGS = ("fr", "en")


def _resolve_locale(lang_param: str | None, profile: UserProfile) -> str:
    """Pick the locale for the privacy text response.

    Priority: explicit ``?lang=`` query param → profile.language →
    ``"fr"``. Anything outside the allow-list collapses to French so a
    malformed header can never produce an empty body.
    """
    if lang_param:
        candidate = lang_param.strip().lower()[:2]
        if candidate in _VALID_LANGS:
            return candidate
    profile_lang = (getattr(profile, "language", "") or "").lower()[:2]
    if profile_lang in _VALID_LANGS:
        return profile_lang
    return "fr"


@router.get("/privacy-text")
async def get_privacy_text(
    request: Request,
    lang: str | None = Query(default=None, max_length=10),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Return the sanitised privacy HTML + DPO contact for the active locale.

    The text is already sanitised on the admin write path (Tiptap →
    bleach). The frontend still passes it through DOMPurify as defence
    in depth, mirroring the Help Center pattern.
    """
    if not await is_gdpr_enabled(db):
        raise _not_found()

    _, profile = up
    locale = _resolve_locale(lang, profile)
    raw = await get_settings_map(db, [
        GDPR_PRIVACY_FR_KEY, GDPR_PRIVACY_EN_KEY, GDPR_DPO_KEY,
    ])
    text_key = GDPR_PRIVACY_EN_KEY if locale == "en" else GDPR_PRIVACY_FR_KEY
    return {
        "lang": locale,
        "text_html": raw.get(text_key) or "",
        "dpo_contact": (raw.get(GDPR_DPO_KEY) or "").strip(),
    }
