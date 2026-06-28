"""Portal notifications bell endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.i18n import get_request_locale
from models.user import User
from models.portal.profile import UserProfile
from api.portal.deps import get_current_profile
from services.portal import notifications as notifs

router = APIRouter(prefix="/notifications", tags=["portal-notifications"])


@router.get("")
async def list_notifs(
    unread_only: bool = Query(False),
    limit: int = Query(notifs.DEFAULT_PAGE_SIZE, ge=1, le=200),
    cursor: str | None = Query(None),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
    locale: str = Depends(get_request_locale),
):
    user, _ = up
    return await notifs.list_for_user(db, user.id, unread_only, limit, cursor, locale)


@router.get("/count")
async def count_notifs(
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    return {"unread": await notifs.count_unread(db, user.id)}


@router.post("/{notif_id}/read")
async def mark_one_read(
    notif_id: int,
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    ok = await notifs.mark_read(db, user.id, notif_id)
    if not ok:
        raise HTTPException(status_code=404, detail="not_found")
    await db.commit()
    return {"ok": True}


@router.post("/read-all")
async def mark_all_read(
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    n = await notifs.mark_all_read(db, user.id)
    await db.commit()
    return {"marked": n}
