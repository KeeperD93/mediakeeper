"""Portal available endpoints: Emby library browsing."""
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.i18n import get_request_locale
from models.user import User
from models.portal.profile import UserProfile
from models.portal.xp_ledger import XpLedger
from api.portal.deps import get_current_profile
from services.portal import available as avail_svc
from services.portal.achievements import safe_check_all_achievements_in_new_session
from services.portal.available_localize import localize_emby_items
from services.tmdb import get_media_detail

router = APIRouter(prefix="/library", tags=["portal-available"])


@router.get("/recent")
async def recently_added(
    limit: int = Query(20, ge=1, le=50),
    locale: str = Depends(get_request_locale),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    items = await avail_svc.get_recently_added(db, limit, enrich_rating=True)
    return {"items": await localize_emby_items(db, items, locale)}


@router.get("/recommended")
async def recommended(
    limit: int = Query(20, ge=1, le=50),
    locale: str = Depends(get_request_locale),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    items = await avail_svc.get_recommended(db, limit)
    return {"items": await localize_emby_items(db, items, locale)}


@router.get("/continue")
async def continue_watching(
    limit: int = Query(10, ge=1, le=30),
    locale: str = Depends(get_request_locale),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    items = await avail_svc.get_continue_watching(db, limit=limit)
    return {"items": await localize_emby_items(db, items, locale)}


@router.get("/genre/{genre_id}")
async def by_genre(
    genre_id: str,
    limit: int = Query(20, ge=1, le=50),
    locale: str = Depends(get_request_locale),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    items = await avail_svc.get_by_genre(db, genre_id, limit)
    return {"items": await localize_emby_items(db, items, locale)}


@router.get("/surprise")
async def surprise_pool(
    background_tasks: BackgroundTasks,
    kind: str = Query(..., pattern="^(movie|tv|manga|documentary)$"),
    limit: int = Query(50, ge=10, le=100),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """
    Random pool of Emby items used by the Surprise overlay to power
    its reveal animation. The frontend asks for a fresh pool every
    time the overlay opens so the pick feels genuinely random.
    """
    user, _ = up
    # Cache scalar attributes BEFORE any commit/rollback. The
    # IntegrityError path that catches duplicate surprise clicks in
    # the same second rolls back the session, which expires the
    # ``user`` instance even when expire_on_commit=False. Accessing
    # ``user.id`` / ``user.username`` post-rollback then triggers a
    # sync lazy reload from the async session → greenlet_spawn.
    viewer_id = user.id
    viewer_username = user.username

    items = await avail_svc.get_surprise_pool(db, kind, limit)

    # Trace each surprise click in the user ledger so the lucky_*
    # family can count usage. xp=0 — the reward is the achievement
    # itself, not the click. Reference is a per-second ISO timestamp
    # so the same user can rack up multiple ticks per day, while a
    # duplicate burst from a flaky network is silently absorbed by
    # the ``uq_xp_user_action_ref`` unique constraint.
    ts_ref = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    db.add(XpLedger(
        user_id=viewer_id,
        action="surprise_used",
        reference=ts_ref,
        xp=0,
    ))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()

    background_tasks.add_task(
        safe_check_all_achievements_in_new_session,
        viewer_id,
        viewer_username,
        "surprise_used",
    )
    return {"items": items}


@router.get("/localized-meta")
async def localized_meta(
    tmdb_id: int = Query(..., gt=0),
    media_type: str = Query(..., pattern="^(movie|tv)$"),
    locale: str = Depends(get_request_locale),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Title + synopsis for one TMDB id, resolved to the viewer locale. The
    Surprise overlay calls this on reveal so the drawn pick shows in the
    viewer's language (the Emby pool serves them in the library's language)."""
    detail = await get_media_detail(media_type, tmdb_id, db, locale)
    return {"title": detail.get("title") or "", "overview": detail.get("overview") or ""}
