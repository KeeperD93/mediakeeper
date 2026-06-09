"""Activity-history row serialization (progress + session-duration data)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from models.playback_stats import PlaybackSession
from services.stats_aggregator.activity import _activity_row_to_dict


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
