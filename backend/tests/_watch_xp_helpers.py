"""Accounts and watched titles for the watch XP tests (fictitious data)."""
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.playback_stats import PlaybackCompletion, PlaybackSession
from models.portal.profile import UserProfile
from models.portal.xp_ledger import XpLedger
from models.user import User

T = datetime(2026, 3, 7, 20, 0, tzinfo=UTC)
TICK = 10_000_000


async def account(db: AsyncSession, name: str = "alice") -> int:
    user = User(username=name, hashed_password="x", is_active=True, must_change_password=False)
    db.add(user)
    await db.flush()
    db.add(UserProfile(user_id=user.id, display_name=name.title(), role="viewer", emby_user_id=f"emby-{name}"))
    await db.commit()
    return user.id


async def watched(
    db: AsyncSession, name: str = "alice", *, item: str = "MOVIE-1", item_type: str = "Movie",
    runtime: int = 7200, at: datetime = T, item_name: str = "Test Movie",
) -> int:
    """A title ``name``'s Emby user watched alone to its end at ``at``; returns the watched title's id."""
    play = PlaybackSession(
        session_key=f"emby-{name}_{item}_{at.timestamp()}", user_id=f"emby-{name}", user_name=name,
        item_id=item, item_name=item_name, item_type=item_type, duration_ticks=runtime * TICK,
        position_ticks=runtime * TICK, started_at=at - timedelta(seconds=runtime), ended_at=at, is_active=False,
        watched_seconds=runtime, exclusive_seconds=runtime, completed_at=at,
    )
    db.add(play)
    await db.flush()
    done = PlaybackCompletion(
        session_id=play.id, user_id=play.user_id, user_name=name, item_id=item, item_type=item_type,
        item_name=item_name, runtime_seconds=runtime, watched_seconds=runtime, exclusive_seconds=runtime,
        completed_at=at,
    )
    db.add(done)
    await db.commit()
    return done.id


async def watch_rows(db: AsyncSession) -> list[tuple[str, str, int]]:
    found = await db.execute(select(XpLedger.action, XpLedger.reference, XpLedger.xp).order_by(XpLedger.id))
    return [tuple(row) for row in found.all()]
