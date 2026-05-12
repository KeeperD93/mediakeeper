"""Portal social activity feed."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.user import User
from models.portal.profile import UserProfile
from api.portal.deps import get_current_profile, get_request_lang
from services.portal.activity import get_activity_feed

router = APIRouter(prefix="/activity", tags=["portal-activity"])


@router.get("")
async def activity_feed(
    limit: int = Query(30, ge=1, le=100),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
    lang: str = Depends(get_request_lang),
):
    try:
        return {"items": await get_activity_feed(db, limit, lang=lang)}
    except Exception:
        return {"items": []}
