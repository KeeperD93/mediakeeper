"""The night of the all-nighter and the months of the king on the clock of a zone."""
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from models.playback_stats import PlaybackSession
from services.portal.playback_algorithms import (
    _chain_covers_all_night,
    has_12_consecutive_top1_months,
)

PARIS = ZoneInfo("Europe/Paris")


def _at(*parts: int) -> datetime:
    return datetime(*parts, tzinfo=UTC)


@pytest.mark.parametrize(
    ("zone", "start", "end", "covers"),
    [
        (UTC, _at(2026, 1, 15, 22), _at(2026, 1, 16, 6), True),
        (UTC, _at(2026, 1, 15, 22, 1), _at(2026, 1, 16, 6), False),
        (UTC, _at(2026, 1, 15, 22), _at(2026, 1, 16, 5, 59), False),
        # Paris, winter: 21:00 to 05:00 UTC.
        (PARIS, _at(2026, 1, 15, 21), _at(2026, 1, 16, 5), True),
        (PARIS, _at(2026, 1, 15, 21, 1), _at(2026, 1, 16, 5), False),
        (PARIS, _at(2026, 1, 15, 21), _at(2026, 1, 16, 4, 59), False),
        (PARIS, _at(2026, 1, 15, 22), _at(2026, 1, 16, 6), False),
        # Paris, summer: 20:00 to 04:00 UTC.
        (PARIS, _at(2026, 7, 15, 20), _at(2026, 7, 16, 4), True),
        (PARIS, _at(2026, 7, 15, 21), _at(2026, 7, 16, 5), False),
        # The clocks go forward: a night of 7 real hours is enough.
        (PARIS, _at(2026, 3, 28, 21), _at(2026, 3, 29, 4), True),
        (PARIS, _at(2026, 3, 28, 21), _at(2026, 3, 29, 3, 59), False),
        # The clocks go back: a night of 9 real hours is needed.
        (PARIS, _at(2026, 10, 24, 20), _at(2026, 10, 25, 5), True),
        (PARIS, _at(2026, 10, 24, 20), _at(2026, 10, 25, 4, 59), False),
        # A longer chain holds the night somewhere inside it.
        (PARIS, _at(2026, 1, 14, 12), _at(2026, 1, 17, 12), True),
        # A chain crossing the end of the year.
        (PARIS, _at(2026, 12, 31, 21), _at(2027, 1, 1, 5), True),
    ],
)
def test_the_all_nighter_follows_the_clock(zone, start, end, covers):
    assert _chain_covers_all_night(start, end, zone) is covers


@pytest.mark.parametrize(
    ("zone", "start"),
    [
        (UTC, datetime(1, 1, 1, tzinfo=UTC)),
        (ZoneInfo("America/New_York"), datetime(1, 1, 1, tzinfo=UTC)),
        (ZoneInfo("Asia/Tokyo"), datetime(9999, 12, 31, 12, tzinfo=UTC)),
    ],
)
def test_a_chain_at_the_edge_of_the_calendar_covers_no_night(zone, start):
    assert _chain_covers_all_night(start, start + timedelta(hours=4), zone) is False


def _session(db, user: str, start: datetime, hours: float) -> None:
    db.add(PlaybackSession(
        session_key=f"{user}-{start.timestamp()}",
        user_id=f"emby-{user}",
        user_name=user,
        item_id="item-1",
        item_name="Test Movie",
        item_type="Movie",
        started_at=start,
        last_seen_at=start,
        ended_at=start + timedelta(hours=hours),
    ))


@pytest.mark.asyncio
async def test_the_king_counts_the_months_of_the_local_calendar(db_session):
    """Bob's long session of December 31 at 23:30 UTC falls in January in Paris."""
    for month in range(1, 13):
        _session(db_session, "alice", _at(2025, month, 15, 12), 2)
        _session(db_session, "bob", _at(2025, month, 15, 12), 1)
    _session(db_session, "bob", _at(2025, 12, 31, 23, 30), 10)
    await db_session.commit()

    assert not await has_12_consecutive_top1_months(db_session, ["emby-alice"], UTC)
    assert await has_12_consecutive_top1_months(db_session, ["emby-alice"], PARIS)


@pytest.mark.asyncio
async def test_the_seconds_of_a_month_stay_real_seconds(db_session):
    """3 real hours across the night the clocks go forward read 4 on the clock of Paris."""
    for month in range(1, 13):
        if month != 3:
            _session(db_session, "alice", _at(2025, month, 15, 12), 2)
            _session(db_session, "bob", _at(2025, month, 15, 12), 1)
    _session(db_session, "alice", _at(2025, 3, 30, 0), 3)
    _session(db_session, "bob", _at(2025, 3, 15, 12), 3.5)
    await db_session.commit()

    assert not await has_12_consecutive_top1_months(db_session, ["emby-alice"], PARIS)
