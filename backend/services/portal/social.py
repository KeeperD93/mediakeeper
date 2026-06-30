"""Ratings, reviews, release reminders.

User-lists logic has been moved to ``services.portal.lists``.
"""
import logging
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.profile import UserProfile
from models.portal.social import (
    UserRating, UserRatingLike, ReleaseReminder,
)
from models.user import User
from services.portal import strip_tags_and_trim

logger = logging.getLogger("mediakeeper.portal.social")


# ── Ratings ──

async def _load_existing_rating(
    db: AsyncSession, user_id: int, tmdb_id: int, media_type: str,
) -> UserRating | None:
    """Lookup helper isolated so concurrency tests can monkeypatch it to
    force the real INSERT path through the unique constraint."""
    result = await db.execute(
        select(UserRating).where(
            UserRating.user_id == user_id,
            UserRating.tmdb_id == tmdb_id,
            UserRating.media_type == media_type,
        )
    )
    return result.scalar_one_or_none()


async def rate_media(
    db: AsyncSession, user_id: int, data: dict
) -> dict:
    review_clean = (
        strip_tags_and_trim(data.get("review", ""), 5000)
        if data.get("review") else None
    )

    rating = await _load_existing_rating(
        db, user_id, data["tmdb_id"], data["media_type"],
    )
    if rating is not None:
        rating.rating = data["rating"]
        rating.review = review_clean
        await db.commit()
        await db.refresh(rating)
        return {"success": True, "id": rating.id}

    new_rating = UserRating(
        user_id=user_id,
        tmdb_id=data["tmdb_id"],
        media_type=data["media_type"],
        rating=data["rating"],
        review=review_clean,
    )
    # The INSERT runs inside a SAVEPOINT so a parallel peer that beat us
    # to ``uq_user_rating`` only invalidates the inner savepoint — the
    # outer transaction stays usable and we can transparently fall back
    # to updating the existing row.
    try:
        async with db.begin_nested():
            db.add(new_rating)
            await db.flush()
    except IntegrityError:
        result = await db.execute(
            select(UserRating).where(
                UserRating.user_id == user_id,
                UserRating.tmdb_id == data["tmdb_id"],
                UserRating.media_type == data["media_type"],
            )
        )
        rating = result.scalar_one()
        rating.rating = data["rating"]
        rating.review = review_clean
        await db.commit()
        await db.refresh(rating)
        return {"success": True, "id": rating.id}

    await db.commit()
    await db.refresh(new_rating)
    return {"success": True, "id": new_rating.id}


async def get_media_ratings(
    db: AsyncSession, tmdb_id: int, media_type: str
) -> list[dict]:
    # Inner-join the author so reviews from soft-deleted or deactivated
    # accounts disappear from the public media page. The rating row
    # survives in ``user_ratings`` (CASCADE on hard purge), it is only
    # hidden — restoring or re-activating the account brings the review
    # back automatically.
    result = await db.execute(
        select(UserRating)
        .join(User, User.id == UserRating.user_id)
        .join(UserProfile, UserProfile.user_id == UserRating.user_id)
        .where(
            UserRating.tmdb_id == tmdb_id,
            UserRating.media_type == media_type,
            User.is_active.is_(True),
            UserProfile.account_active.is_(True),
            UserProfile.deleted_at.is_(None),
        )
        .order_by(UserRating.id.desc())
        .limit(50)
    )
    return [_serialize_rating(r) for r in result.scalars().all()]


async def _load_existing_like(
    db: AsyncSession, rating_id: int, user_id: int,
) -> UserRatingLike | None:
    """Lookup helper isolated so concurrency tests can monkeypatch it to
    drive the real INSERT path through ``uq_rating_like``."""
    result = await db.execute(
        select(UserRatingLike).where(
            UserRatingLike.rating_id == rating_id,
            UserRatingLike.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def toggle_rating_like(
    db: AsyncSession, rating_id: int, user_id: int
) -> dict:
    like = await _load_existing_like(db, rating_id, user_id)
    if like is not None:
        # A keyed DELETE statement is naturally idempotent: if the row
        # vanished concurrently between the load and here, the statement
        # affects 0 rows without raising — unlike ``session.delete()``,
        # which can surface ``StaleDataError`` on flush.
        await db.execute(
            delete(UserRatingLike).where(UserRatingLike.id == like.id)
        )
        await db.commit()
        return {"success": True, "action": "removed"}

    # Two concurrent toggles starting from "no like" both want to add the
    # same row; the unique constraint makes one of them fail. We treat
    # the loser as a successful add — the user's intent (be in the
    # "liked" state) is satisfied, and the row count stays at 1.
    try:
        async with db.begin_nested():
            db.add(UserRatingLike(rating_id=rating_id, user_id=user_id))
            await db.flush()
    except IntegrityError:
        logger.debug(
            "[LIKE] race avoided rating_id=%s user_id=%s "
            "— concurrent insert won, idempotent add",
            rating_id, user_id,
        )
    await db.commit()
    return {"success": True, "action": "added"}


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
