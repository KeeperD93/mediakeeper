"""Merging or deleting a user's stats keeps watched titles and pauses with the sessions."""
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from models.playback_stats import PlaybackCompletion, PlaybackPauseEvent, PlaybackSession
from services.stats_aggregator import delete_user_stats, merge_user_stats

AT = datetime(2026, 3, 7, 20, 0, tzinfo=timezone.utc)


async def _seed(db, user_id: str, name: str, key: str) -> None:
    row = PlaybackSession(
        session_key=key, emby_session_key=key, user_id=user_id, user_name=name, item_id="MOVIE-1",
        item_name="Sample title", item_type="Movie", started_at=AT, last_seen_at=AT, is_active=False,
    )
    db.add(row)
    await db.flush()
    db.add(PlaybackCompletion(
        session_id=row.id, user_id=user_id, user_name=name, item_id="MOVIE-1", item_type="Movie",
        item_name="Sample title", runtime_seconds=600, watched_seconds=600, completed_at=AT,
    ))
    db.add(PlaybackPauseEvent(
        session_key=key, user_id=user_id, user_name=name, item_id="MOVIE-1",
        item_name="Sample title", item_type="Movie", pause_started_at=AT,
    ))
    await db.commit()


async def _owners(db, model) -> list[tuple[str, str]]:
    return sorted((await db.execute(select(model.user_id, model.user_name))).all())


@pytest.mark.asyncio
async def test_merge_moves_watched_titles_and_pauses_too(db_session):
    await _seed(db_session, "OLD", "old-name", "k-old")
    await _seed(db_session, "NEW", "new-name", "k-new")
    assert await merge_user_stats(db_session, "OLD", "NEW") == 1
    for model in (PlaybackSession, PlaybackCompletion, PlaybackPauseEvent):
        assert await _owners(db_session, model) == [("NEW", "new-name"), ("NEW", "new-name")]


@pytest.mark.asyncio
async def test_delete_removes_watched_titles_and_pauses_too(db_session):
    await _seed(db_session, "GONE", "gone", "k-gone")
    await _seed(db_session, "KEPT", "kept", "k-kept")
    assert await delete_user_stats(db_session, "GONE") == 1
    for model in (PlaybackSession, PlaybackCompletion, PlaybackPauseEvent):
        assert await _owners(db_session, model) == [("KEPT", "kept")]
