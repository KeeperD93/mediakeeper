"""Activity-history row serialization (progress + session-duration data)
and the ephemeral exclude-users display filter."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from models.playback_stats import PlaybackSession
from services.stats_aggregator.activity import (
    _activity_row_to_dict,
    get_activity_history,
    get_activity_users,
)


def _ticks(minutes: float) -> int:
    return int(minutes * 60 * 1e7)  # Emby uses 100ns ticks (1e7 per second)


def _row(**kw) -> PlaybackSession:
    base = dict(
        id=1, session_key="k", user_id="u1", user_name="Alice",
        item_id="m1", item_name="Film", item_type="Movie",
    )
    base.update(kw)
    return PlaybackSession(**base)


def test_activity_row_exposes_position_and_runtime():
    d = _activity_row_to_dict(_row(duration_ticks=_ticks(114), position_ticks=_ticks(89)))
    assert d["runtime_ticks"] == _ticks(114)  # total media length
    assert d["position_ticks"] == _ticks(89)  # how far the session reached


def test_session_ticks_is_the_active_span():
    start = datetime(2026, 1, 1, 20, 0, tzinfo=timezone.utc)
    d = _activity_row_to_dict(_row(
        duration_ticks=_ticks(62.5), position_ticks=_ticks(55),
        started_at=start, last_seen_at=start + timedelta(minutes=25),
    ))
    # The session lasted 25 min even though it reached the 55-min mark (resume).
    assert d["session_ticks"] == _ticks(25)


def test_session_ticks_capped_at_runtime_for_never_closed_sessions():
    start = datetime(2026, 1, 1, 20, 0, tzinfo=timezone.utc)
    d = _activity_row_to_dict(_row(
        duration_ticks=_ticks(60), position_ticks=_ticks(60),
        started_at=start, last_seen_at=start + timedelta(days=2),  # ghost session
    ))
    assert d["session_ticks"] == _ticks(60)  # capped at the media runtime


def test_runtime_and_session_default_to_zero_when_unknown():
    d = _activity_row_to_dict(_row(duration_ticks=None, position_ticks=_ticks(5)))
    assert d["runtime_ticks"] == 0
    assert d["session_ticks"] == 0  # no timestamps -> no span


@pytest.mark.asyncio
async def test_get_activity_history_excludes_users(db_session):
    db_session.add_all([
        _row(id=1, session_key="s1", user_id="A", user_name="Admin"),
        _row(id=2, session_key="s2", user_id="A", user_name="Admin"),
        _row(id=3, session_key="s3", user_id="B", user_name="Bob"),
    ])
    await db_session.commit()

    full = await get_activity_history(db_session)
    assert full["total"] == 3

    filtered = await get_activity_history(db_session, exclude_users="A")
    assert filtered["total"] == 1
    assert [it["user_id"] for it in filtered["items"]] == ["B"]


@pytest.mark.asyncio
async def test_get_activity_history_ignores_empty_exclude(db_session):
    db_session.add(_row(id=1, session_key="s1", user_id="A", user_name="Admin"))
    await db_session.commit()
    res = await get_activity_history(db_session, exclude_users="")
    assert res["total"] == 1


@pytest.mark.asyncio
async def test_get_activity_users_returns_distinct(db_session):
    db_session.add_all([
        _row(id=1, session_key="s1", user_id="A", user_name="Admin"),
        _row(id=2, session_key="s2", user_id="A", user_name="Admin"),
        _row(id=3, session_key="s3", user_id="B", user_name="Bob"),
    ])
    await db_session.commit()
    users = await get_activity_users(db_session)
    assert {u["id"] for u in users} == {"A", "B"}
    assert {u["name"] for u in users} == {"Admin", "Bob"}
