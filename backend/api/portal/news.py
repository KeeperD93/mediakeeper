"""Portal news endpoints."""
from datetime import datetime
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.user import User
from models.portal.profile import UserProfile
from api.portal.deps import get_current_profile, require_admin
from services.portal import news as news_svc

router = APIRouter(prefix="/news", tags=["portal-news"])


def _clean_image_url(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("invalid_image_url")
    return value


class CreateNews(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=300)
    content: str = Field(..., min_length=1, max_length=10000)
    image_url: Optional[str] = Field(None, max_length=500)
    type: str = Field("announcement", pattern="^(announcement|additions|maintenance|event|other)$")
    pinned: bool = False
    notify_discord: bool = False
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, value: str | None) -> str | None:
        return _clean_image_url(value)


class UpdateNews(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(None, min_length=1, max_length=300)
    content: Optional[str] = Field(None, min_length=1, max_length=10000)
    image_url: Optional[str] = Field(None, max_length=500)
    type: Optional[str] = Field(None, pattern="^(announcement|additions|maintenance|event|other)$")
    pinned: Optional[bool] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, value: str | None) -> str | None:
        return _clean_image_url(value)


@router.get("")
async def list_news(
    cursor: Optional[str] = None,
    limit: int = Query(20, ge=1, le=50),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    return await news_svc.list_news(db, cursor, limit, respect_schedule=True)


@router.get("/admin")
async def list_news_admin(
    cursor: Optional[str] = None,
    limit: int = Query(20, ge=1, le=50),
    admin: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin list — bypasses the schedule filter so future/expired posts stay visible."""
    return await news_svc.list_news(db, cursor, limit, respect_schedule=False)


@router.get("/unread")
async def get_unread(
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    items = await news_svc.get_unread_news(db, user.id)
    return {"items": items}


@router.post("/read/{news_id}")
async def mark_read(
    news_id: int,
    dismissed: bool = Query(False),
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    user, _ = up
    return await news_svc.mark_news_read(db, news_id, user.id, dismissed)


@router.post("")
async def create_news(
    data: CreateNews,
    admin: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user, _ = admin
    try:
        return await news_svc.create_news(db, user.id, data.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/{news_id}")
async def update_news(
    news_id: int,
    data: UpdateNews,
    admin: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await news_svc.update_news(db, news_id, data.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.delete("/{news_id}")
async def delete_news(
    news_id: int,
    admin: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await news_svc.delete_news(db, news_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
