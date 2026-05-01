"""Compute seasonal unlock years per achievement (for UI year badges)."""
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.profile import UserProfile
from models.playback_stats import PlaybackSession
from services.portal.exclusions import get_exclusion_filters


async def _compute_seasonal_years(
    db: AsyncSession, user_id: int
) -> dict[str, list[int]]:
    """
    For each seasonal/dated secret, return a sorted list of years where the
    condition was met (so the UI can show "2026, 2027" badges on the trophy).
    """
    from models.user import User

    profile = (await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )).scalar_one_or_none()
    user_obj = await db.get(User, user_id)
    names = []
    for c in (user_obj.username if user_obj else None, profile.display_name if profile else None):
        if c and c not in names:
            names.append(c)
    if not names:
        return {}

    excl = await get_exclusion_filters(db)
    base_filter = PlaybackSession.user_name.in_(names)

    result: dict[str, list[int]] = {}

    async def _years_for(extra_filter) -> list[int]:
        rows = (await db.execute(
            select(func.extract("year", PlaybackSession.started_at).label("yr"))
            .where(base_filter, *excl, extra_filter)
            .distinct()
        )).all()
        return sorted({int(r.yr) for r in rows if r.yr})

    # Christmas — December with christmas content (simplified: any december play)
    result["secret_christmas"] = await _years_for(
        func.extract("month", PlaybackSession.started_at) == 12
    )
    # Halloween — October 31
    result["secret_halloween"] = await _years_for(
        and_(
            func.extract("month", PlaybackSession.started_at) == 10,
            func.extract("day", PlaybackSession.started_at) == 31,
        )
    )
    # Valentine — February 14
    result["secret_valentine"] = await _years_for(
        and_(
            func.extract("month", PlaybackSession.started_at) == 2,
            func.extract("day", PlaybackSession.started_at) == 14,
        )
    )
    # New Year — January 1 before 1am
    result["secret_newyear"] = await _years_for(
        and_(
            func.extract("month", PlaybackSession.started_at) == 1,
            func.extract("day", PlaybackSession.started_at) == 1,
            func.extract("hour", PlaybackSession.started_at) < 1,
        )
    )
    # Summer Vibes — July/August
    result["secret_summer"] = await _years_for(
        func.extract("month", PlaybackSession.started_at).in_([7, 8])
    )
    # Friday 13 — any Friday the 13th (year of that play)
    fri13_rows = (await db.execute(
        select(PlaybackSession.started_at)
        .where(
            base_filter, *excl,
            func.extract("day", PlaybackSession.started_at) == 13,
        )
    )).all()
    fri_years = set()
    for r in fri13_rows:
        if r.started_at and r.started_at.weekday() == 4:
            fri_years.add(r.started_at.year)
    result["secret_friday13"] = sorted(fri_years)

    return result
