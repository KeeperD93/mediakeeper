"""Portal daily digest endpoints — viewer-scoped.

Exposes the once-per-day "Quoi de neuf aujourd'hui ?" payload plus a dismiss
endpoint so the frontend can skip the overlay for the rest of the calendar
day, and the compact or full view the viewer picked for it.
"""
import asyncio

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, StrictBool
from sqlalchemy.ext.asyncio import AsyncSession

from api.portal.deps import get_current_profile, get_request_lang
from core.database import get_db
from core.i18n import get_request_locale
from core.rate_limit import limiter, portal_user_or_ip_key
from models.portal.profile import UserProfile
from models.user import User
from services.portal import daily_digest as dd_svc

router = APIRouter(prefix="/daily-digest", tags=["portal-daily-digest"])


class DigestView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    compact: StrictBool


@router.get("")
@limiter.limit("20/minute", key_func=portal_user_or_ip_key)
async def get_daily_digest(
    request: Request,
    force: bool = Query(False, description="Bypass the 1h in-memory cache"),
    db: AsyncSession = Depends(get_db),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    lang: str = Depends(get_request_locale),
    name_lang: str = Depends(get_request_lang),
):
    """Return the digest payload, whether it was dismissed today and the picked view.

    The frontend auto-trigger on layout mount should NOT show the overlay
    when ``dismissed`` is true or ``digest.empty`` is true. The manual
    reopen flow (avatar menu) displays it regardless of ``dismissed``.
    """
    # Lazy: api.portal_changelog loads api.portal.deps, so this package is mid-import.
    from api.portal_changelog import latest_release

    user, _ = up
    dismissed = await dd_svc.is_dismissed_today(db, user.id)
    compact = await dd_svc.is_compact(db, user.id)
    release = await asyncio.to_thread(latest_release, name_lang)
    digest = await dd_svc.build_digest(
        db, user, use_cache=not force, lang=lang, name_lang=name_lang, release=release,
    )
    return {
        "dismissed": dismissed,
        "compact": compact,
        "digest": digest,
    }


@router.post("/dismiss")
async def dismiss_daily_digest(
    db: AsyncSession = Depends(get_db),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
):
    """Mark today's digest as dismissed for the current user."""
    # Lazy: api.portal_changelog loads api.portal.deps, so this package is mid-import.
    from api.portal_changelog import PORTAL_VERSION

    user, _ = up
    date = await dd_svc.mark_dismissed(db, user.id, release_version=PORTAL_VERSION)
    return {"success": True, "date": date}


@router.put("/view")
@limiter.limit("30/minute", key_func=portal_user_or_ip_key)
async def set_daily_digest_view(
    request: Request,
    data: DigestView,
    db: AsyncSession = Depends(get_db),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
):
    """Remember the compact or full view of the overlay for the current user."""
    user, _ = up
    return {"compact": await dd_svc.set_compact(db, user.id, data.compact)}
