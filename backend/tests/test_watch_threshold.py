"""Unit + integration tests for the shared watch-threshold helpers.

``session_meets_threshold`` (pure Python) and ``watched_session_filter``
(SQLAlchemy expression) live in ``services.portal._watch_threshold`` and
must agree on which playback rows count as "actually watched". The pure
helper has two branches (live rows with a real ``duration_ticks`` and
legacy Playback-Reporting rows where ``duration_ticks`` is ``0`` /
``NULL``); the table below pins down both.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from models.playback_stats import PlaybackSession
from services.portal._watch_threshold import (
    LEGACY_MIN_TICKS,
    session_meets_threshold,
    watched_session_filter,
)


# ---------------------------------------------------------------------------
# Pure-Python helper — branch coverage
# ---------------------------------------------------------------------------


def test_session_meets_threshold_live_above():
    # 90% of a fictive 100-tick runtime — well over the 85% bar.
    assert session_meets_threshold(90, 100) is True


def test_session_meets_threshold_live_exactly_at_threshold():
    # 85 / 100 == 0.85 — boundary. The check is ``>=``, so this passes.
    assert session_meets_threshold(85, 100) is True


def test_session_meets_threshold_live_below():
    assert session_meets_threshold(80, 100) is False


def test_session_meets_threshold_legacy_above_60s():
    # 700M ticks ≈ 70 s, comfortably above the 60 s floor.
    assert session_meets_threshold(700_000_000, 0) is True


def test_session_meets_threshold_legacy_exactly_at_60s():
    # 600M ticks == LEGACY_MIN_TICKS — boundary, ``>=`` lets it through.
    assert session_meets_threshold(LEGACY_MIN_TICKS, 0) is True


def test_session_meets_threshold_legacy_below_60s():
    # 300M ticks ≈ 30 s — sampling, not viewing.
    assert session_meets_threshold(300_000_000, 0) is False


def test_session_meets_threshold_legacy_null_duration():
    # ``duration_ticks=NULL`` is the original Playback-Reporting shape;
    # the helper coerces NULL to 0 and falls into the legacy branch.
    assert session_meets_threshold(700_000_000, None) is True


def test_session_meets_threshold_null_position_returns_false():
    # No position recorded — nothing was actually watched, regardless
    # of which branch we'd otherwise land in.
    assert session_meets_threshold(None, 100) is False


def test_session_meets_threshold_both_null_returns_false():
    assert session_meets_threshold(None, None) is False


# ---------------------------------------------------------------------------
# SQL filter — same rules expressed as a SQLAlchemy WHERE clause
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_watched_session_filter_matches_python_helper(db_session):
    """Round-trip: insert one row per branch, confirm only the rows
    ``session_meets_threshold`` accepts also pass the SQL filter."""
    now = datetime.now(timezone.utc)

    rows = [
        # Live row, 90% played — ABOVE threshold.
        PlaybackSession(
            session_key="LIVE-OK",
            user_id="U1",
            user_name="u1",
            item_id="I1",
            item_name="Live OK",
            item_type="Movie",
            duration_ticks=1_000_000_000,
            position_ticks=900_000_000,
            started_at=now,
            last_seen_at=now,
        ),
        # Live row, 50% played — BELOW threshold.
        PlaybackSession(
            session_key="LIVE-LOW",
            user_id="U1",
            user_name="u1",
            item_id="I2",
            item_name="Live Low",
            item_type="Movie",
            duration_ticks=1_000_000_000,
            position_ticks=500_000_000,
            started_at=now,
            last_seen_at=now,
        ),
        # Legacy row (duration_ticks=0), position ≈ 70 s — ABOVE floor.
        PlaybackSession(
            session_key="LEGACY-OK",
            user_id="U1",
            user_name="u1",
            item_id="I3",
            item_name="Legacy OK",
            item_type="Movie",
            duration_ticks=0,
            position_ticks=700_000_000,
            started_at=now,
            last_seen_at=now,
        ),
        # Legacy row, position ≈ 30 s — BELOW floor.
        PlaybackSession(
            session_key="LEGACY-LOW",
            user_id="U1",
            user_name="u1",
            item_id="I4",
            item_name="Legacy Low",
            item_type="Movie",
            duration_ticks=0,
            position_ticks=300_000_000,
            started_at=now,
            last_seen_at=now,
        ),
    ]
    db_session.add_all(rows)
    await db_session.commit()

    result = await db_session.execute(
        select(PlaybackSession.session_key).where(watched_session_filter())
    )
    keys = {row[0] for row in result.all()}
    assert keys == {"LIVE-OK", "LEGACY-OK"}
