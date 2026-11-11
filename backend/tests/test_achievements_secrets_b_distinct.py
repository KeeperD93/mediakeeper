"""The secret checks that list a player's media-server ids compile without
SQLAlchemy's unary ``distinct()`` warning, and still find the other player."""
import logging
import warnings
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import SAWarning
from sqlalchemy.ext.asyncio import AsyncSession

from models.playback_stats import PlaybackSession
from services.portal.achievements import check_all_achievements, seed_achievements
from tests._portal_profile_helpers import make_portal_user

UNARY_DISTINCT = "Column-expression-level unary distinct"


def _play(db, name: str, started: datetime, hours: float) -> None:
    ended = started + timedelta(hours=hours)
    db.add(PlaybackSession(
        session_key=f"emby-{name}-{started.timestamp()}", user_id=f"emby-{name}",
        user_name=name, item_id="movie-1", item_name="Test Movie", item_type="Movie",
        started_at=started, last_seen_at=ended, ended_at=ended, is_active=False,
    ))


@pytest.mark.asyncio
async def test_the_cross_player_checks_run_without_the_distinct_warning(db_session, caplog):
    alice, _ = await make_portal_user(db_session, username="alice")
    await make_portal_user(db_session, username="bob")
    await seed_achievements(db_session)
    start = datetime(2026, 4, 10, 20, tzinfo=UTC)
    _play(db_session, "alice", start, 2)
    _play(db_session, "bob", start + timedelta(minutes=15), 1.5)
    await db_session.commit()

    # No statement cache: a query an earlier test compiled would not warn again.
    uncached = db_session.bind.execution_options(compiled_cache=None)
    async with AsyncSession(uncached, expire_on_commit=False) as session:
        with warnings.catch_warnings(), caplog.at_level(
            logging.ERROR, logger="mediakeeper.portal.achievements",
        ):
            warnings.filterwarnings("error", message=UNARY_DISTINCT, category=SAWarning)
            unlocks = await check_all_achievements(session, alice.id)

    assert "check pass failed" not in caplog.text
    assert "secret_sync" in {u["achievement_id"] for u in unlocks}
