"""Ratings, reviews, release reminders.

User-lists logic has been moved to ``services.portal.lists``.
"""
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.social import (
    UserRating, UserRatingLike, ReleaseReminder,
)
from services.portal import sanitize

logger = logging.getLogger("mediakeeper.portal.social")


# ── Ratings ──

async def rate_media(
    db: AsyncSession, user_id: int, data: dict
) -> dict:
    result = await db.execute(
        select(UserRating).where(
            UserRating.user_id == user_id,
            UserRating.tmdb_id == data["tmdb_id"],
            UserRating.media_type == data["media_type"],
        )
    )
    rating = result.scalar_one_or_none()
    if rating:
        rating.rating = data["rating"]
        rating.review = sanitize(data.get("review", ""), 5000) if data.get("review") else None
    else:
        rating = UserRating(
            user_id=user_id,
            tmdb_id=data["tmdb_id"],
            media_type=data["media_type"],
            rating=data["rating"],
            review=sanitize(data.get("review", ""), 5000) if data.get("review") else None,
        )
    db.add(rating)
    await db.commit()
    await db.refresh(rating)
    return {"success": True, "id": rating.id}


async def get_media_ratings(
    db: AsyncSession, tmdb_id: int, media_type: str
) -> list[dict]:
    result = await db.execute(
        select(UserRating)
        .where(UserRating.tmdb_id == tmdb_id, UserRating.media_type == media_type)
        .order_by(UserRating.id.desc())
        .limit(50)
    )
    return [_serialize_rating(r) for r in result.scalars().all()]


async def toggle_rating_like(
    db: AsyncSession, rating_id: int, user_id: int
) -> dict:
    existing = await db.execute(
        select(UserRatingLike).where(
            UserRatingLike.rating_id == rating_id,
            UserRatingLike.user_id == user_id,
        )
    )
    like = existing.scalar_one_or_none()
    if like:
        await db.delete(like)
        action = "removed"
    else:
        db.add(UserRatingLike(rating_id=rating_id, user_id=user_id))
        action = "added"
    await db.commit()
    return {"success": True, "action": action}


# ── Release reminders ──

async def add_reminder(
    db: AsyncSession, user_id: int, tmdb_id: int, media_type: str, release_date=None
) -> dict:
    existing = await db.execute(
        select(ReleaseReminder).where(
            ReleaseReminder.user_id == user_id,
            ReleaseReminder.tmdb_id == tmdb_id,
        )
    )
    if existing.scalar_one_or_none():
        return {"error": "already_exists"}
    reminder = ReleaseReminder(
        user_id=user_id, tmdb_id=tmdb_id,
        media_type=media_type, release_date=release_date,
    )
    db.add(reminder)
    await db.commit()
    return {"success": True}


async def remove_reminder(
    db: AsyncSession, user_id: int, tmdb_id: int
) -> dict:
    result = await db.execute(
        select(ReleaseReminder).where(
            ReleaseReminder.user_id == user_id,
            ReleaseReminder.tmdb_id == tmdb_id,
        )
    )
    reminder = result.scalar_one_or_none()
    if reminder:
        await db.delete(reminder)
        await db.commit()
    return {"success": True}


async def get_user_reminders(db: AsyncSession, user_id: int) -> list[dict]:
    result = await db.execute(
        select(ReleaseReminder)
        .where(ReleaseReminder.user_id == user_id, ReleaseReminder.notified == False)  # noqa: E712
        .order_by(ReleaseReminder.release_date)
    )
    return [{
        "tmdb_id": r.tmdb_id, "media_type": r.media_type,
        "release_date": r.release_date.isoformat() if r.release_date else None,
    } for r in result.scalars().all()]


def _serialize_rating(r: UserRating) -> dict:
    return {
        "id": r.id, "user_id": r.user_id,
        "tmdb_id": r.tmdb_id, "media_type": r.media_type,
        "rating": r.rating, "review": r.review,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
