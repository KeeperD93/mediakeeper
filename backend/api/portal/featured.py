"""Featured heroes: admin manages, public reads."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.user import User
from models.portal.profile import UserProfile
from models.portal.featured import FeaturedHero
from api.portal.deps import get_current_profile, require_admin
from services.portal.image_urls import safe_image_url

router = APIRouter(prefix="/featured", tags=["portal-featured"])
logger = logging.getLogger("mediakeeper.portal.featured")


class AddFeatured(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tmdb_id: int
    media_type: str = Field(..., pattern="^(movie|tv)$")
    title: str = Field(..., min_length=1, max_length=500)
    overview: str | None = Field(None, max_length=2000)
    poster_url: str | None = Field(None, max_length=500)
    backdrop: str | None = Field(None, max_length=500)
    vote: float | None = Field(None, ge=0, le=10)  # TMDB score; refuses NaN
    year: str | None = Field(None, max_length=10)
    sort_order: int = 0

    # Stored, then re-served into the home banner (background-image sink):
    # same rule as requests and lists.
    @field_validator("poster_url", "backdrop")
    @classmethod
    def _safe_image_url(cls, v: str | None) -> str | None:
        return safe_image_url(v)


class UpdateFeatured(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sort_order: int | None = None
    active: bool | None = None


@router.get("")
async def list_featured(
    up: tuple[User, UserProfile] = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
):
    """Public: get active featured heroes (sorted by sort_order).

    The response also piggybacks ``hero_trend_count`` so the home page
    can size its hero banner without a second round-trip. This setting
    is admin-writable via PATCH /admin/settings and defaults to 10.
    """
    from services.portal.admin import get_portal_int
    result = await db.execute(
        select(FeaturedHero)
        .where(FeaturedHero.active == True)  # noqa: E712
        .order_by(FeaturedHero.sort_order, FeaturedHero.id.desc())
    )
    hero_trend_count = await get_portal_int(db, "portal.hero_trend_count")
    return {
        "items": [_serialize(f) for f in result.scalars().all()],
        "hero_trend_count": hero_trend_count,
    }


@router.get("/all")
async def list_all_featured(
    admin: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: get all featured heroes (including inactive)."""
    result = await db.execute(
        select(FeaturedHero).order_by(FeaturedHero.sort_order, FeaturedHero.id.desc())
    )
    return {"items": [_serialize(f) for f in result.scalars().all()]}


@router.post("")
async def add_featured(
    data: AddFeatured,
    admin: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: add a media to featured heroes."""
    user, _ = admin
    hero = FeaturedHero(
        tmdb_id=data.tmdb_id,
        media_type=data.media_type,
        title=data.title,
        overview=data.overview,
        poster_url=data.poster_url,
        backdrop=data.backdrop,
        vote=data.vote,
        year=data.year,
        sort_order=data.sort_order,
        added_by=user.id,
    )
    db.add(hero)
    await db.commit()
    await db.refresh(hero)
    logger.info("[FEATURED] Added #%s '%s' by user_id=%s", hero.id, data.title, user.id)
    return {"success": True, "id": hero.id}


@router.put("/{hero_id}")
async def update_featured(
    hero_id: int,
    data: UpdateFeatured,
    admin: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: update sort order or active status."""
    hero = await db.get(FeaturedHero, hero_id)
    if not hero:
        raise HTTPException(status_code=404, detail="not_found")
    if data.sort_order is not None:
        hero.sort_order = data.sort_order
    if data.active is not None:
        hero.active = data.active
    db.add(hero)
    await db.commit()
    return {"success": True}


@router.delete("/{hero_id}")
async def delete_featured(
    hero_id: int,
    admin: tuple[User, UserProfile] = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: remove from featured."""
    hero = await db.get(FeaturedHero, hero_id)
    if not hero:
        raise HTTPException(status_code=404, detail="not_found")
    await db.delete(hero)
    await db.commit()
    logger.info("[FEATURED] Removed #%s", hero_id)
    return {"success": True}


def _serialize(f: FeaturedHero) -> dict:
    return {
        "id": f.id,
        "tmdb_id": f.tmdb_id,
        "media_type": f.media_type,
        "title": f.title,
        "overview": f.overview,
        "poster_url": f.poster_url,
        "backdrop": f.backdrop,
        "vote": f.vote,
        "year": f.year,
        "sort_order": f.sort_order,
        "active": f.active,
    }
