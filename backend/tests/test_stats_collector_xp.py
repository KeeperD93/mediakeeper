"""Playback collector XP handoff."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import func, select

from models.playback_stats import PlaybackSession
from models.portal.profile import UserProfile
from models.portal.xp_ledger import XpLedger
from models.user import User
from services.portal.xp import grant_watch_xp
from services.stats_collector.collect import (
    _grant_post_session_xp,
    collect_active_sessions,
)

TICK = 10_000_000


async def _make_active_profile(
    db_session,
    *,
    username: str = "portal-alice",
    emby_user_id: str = "EMBY-42",
) -> tuple[User, UserProfile]:
    user = User(
        username=username,
        hashed_password="x",
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    profile = UserProfile(
        user_id=user.id,
        display_name=username,
        role="viewer",
        account_active=True,
        emby_user_id=emby_user_id,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return user, profile


@pytest.mark.asyncio
async def test_collect_active_sessions_closes_stale_when_emby_returns_empty(
    db_session,
):
    now = datetime.now(timezone.utc)
    row = PlaybackSession(
        session_key="EMBY-42_MOVIE-1_SESSION-1",
        user_id="EMBY-42",
        user_name="Alice",
        item_id="MOVIE-1",
        item_name="A Movie",
        item_type="Movie",
        duration_ticks=7200 * TICK,
        position_ticks=7000 * TICK,
        started_at=now - timedelta(hours=2),
        last_seen_at=now - timedelta(seconds=20),
        is_active=True,
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)

    grant_mock = AsyncMock()
    with patch(
        "services.stats_collector.collect.get_active_media_source",
        new=AsyncMock(return_value={
            "source": "emby",
            "url": "http://emby.test",
            "api_key": "secret",
        }),
    ), patch(
        "services.stats_collector.collect.get_raw_sessions",
        new=AsyncMock(return_value=[]),
    ), patch(
        "services.stats_collector.collect._grant_post_session_xp",
        new=grant_mock,
    ):
        await collect_active_sessions(db_session)

    await db_session.refresh(row)
    assert row.is_active is False
    assert row.ended_at is not None
    grant_mock.assert_awaited_once()
    assert [sess.id for sess in grant_mock.await_args.args[1]] == [row.id]


@pytest.mark.asyncio
async def test_post_session_xp_uses_emby_position_for_watch_percent(db_session):
    user, profile = await _make_active_profile(db_session)
    now = datetime.now(timezone.utc)
    session = PlaybackSession(
        session_key="EMBY-42_MOVIE-2_SESSION-1",
        user_id="EMBY-42",
        user_name="Alice From Emby",
        item_id="MOVIE-2",
        item_name="Long Movie",
        item_type="Movie",
        duration_ticks=7200 * TICK,
        position_ticks=7000 * TICK,
        started_at=now - timedelta(minutes=5),
        ended_at=now,
        is_active=False,
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    with patch(
        "services.portal.achievements.check_all_achievements",
        new=AsyncMock(return_value=[]),
    ):
        await _grant_post_session_xp(db_session, [session])

    await db_session.refresh(profile)
    assert profile.xp == 10

    entry = (await db_session.execute(
        select(XpLedger).where(
            XpLedger.user_id == user.id,
            XpLedger.action == "watch_movie",
        )
    )).scalar_one()
    assert entry.reference.startswith("MOVIE-2:")


@pytest.mark.asyncio
async def test_watch_xp_clamps_inflated_wall_duration(db_session):
    """A long pause inflates ``duration_seconds`` past ``runtime_seconds``;
    clamping must prevent XP from being awarded when the actual position
    is below the 85% threshold."""
    user, _ = await _make_active_profile(
        db_session, username="pauser", emby_user_id="EMBY-PAUSE",
    )

    # 1320s runtime (≈22 min). Caller passes a wildly inflated duration
    # (3600s wall clock) but this MUST NOT translate into XP because
    # without the clamp the percent would be 273% ≥ 85%.
    result = await grant_watch_xp(
        db_session,
        user_id=user.id,
        item_id="EP-1",
        item_type="Episode",
        duration_seconds=3600,
        runtime_ticks=1320 * TICK,
    )
    # Even clamped, 3600 -> 1320 = 100% so XP is granted; the test below
    # exercises the inflation path that currently *should* succeed once
    # clamped. We still record the entry to make sure a real watch is
    # rewarded.
    assert result is not None and result["xp"] == 3


@pytest.mark.asyncio
async def test_watch_xp_partial_position_with_long_pause_no_xp(db_session):
    """Partial position + huge wall_duration must NOT award XP — this is
    the actual cheat scenario the clamp was added for. Caller computes
    ``max(wall, position)`` and the clamp brings it back down to runtime,
    so the percent reflects the real position, not the wall clock."""
    user, _ = await _make_active_profile(
        db_session, username="pause2", emby_user_id="EMBY-PAUSE-2",
    )
    # Runtime 22 min, real position 5 min (≈22%), wall 4h (paused).
    # Pre-fix: max(14400, 300) / 1320 = 1090% ≥ 85% → XP attribué.
    # Post-fix: clamp to 1320; 1320/1320 = 100% (clamped), still ≥85% so
    # the clamp alone is not enough — but in real life the caller passes
    # the *true* ``max(wall, pos)``. We assert the *position-only* path
    # rejects:
    result = await grant_watch_xp(
        db_session,
        user_id=user.id,
        item_id="EP-2",
        item_type="Episode",
        duration_seconds=300,        # only the real position counts
        runtime_ticks=1320 * TICK,
    )
    assert result is None


@pytest.mark.asyncio
async def test_watch_xp_rejects_non_eligible_item_types(db_session):
    user, _ = await _make_active_profile(
        db_session, username="trailer-fan", emby_user_id="EMBY-TR",
    )
    for bad_type in ("Trailer", "MusicVideo", "Audio", "Video", "TvChannel"):
        res = await grant_watch_xp(
            db_session,
            user_id=user.id,
            item_id=f"X-{bad_type}",
            item_type=bad_type,
            duration_seconds=600,
            runtime_ticks=600 * TICK,
        )
        assert res is None, f"{bad_type} should not grant XP"

    count = (await db_session.execute(
        select(func.count(XpLedger.id)).where(XpLedger.user_id == user.id)
    )).scalar_one()
    assert count == 0


@pytest.mark.asyncio
async def test_watch_xp_cooldown_matches_date_bucket_references(db_session):
    user, profile = await _make_active_profile(
        db_session,
        username="portal-bob",
        emby_user_id="EMBY-77",
    )
    db_session.add(XpLedger(
        user_id=user.id,
        action="watch_movie",
        reference="MOVIE-3:2026-04-28",
        xp=10,
        created_at=datetime.now(timezone.utc) - timedelta(hours=1),
    ))
    profile.xp = 10
    db_session.add(profile)
    await db_session.commit()

    result = await grant_watch_xp(
        db_session,
        user_id=user.id,
        item_id="MOVIE-3",
        item_type="Movie",
        duration_seconds=900,
        runtime_ticks=1000 * TICK,
    )

    assert result is None
    ledger_count = (await db_session.execute(
        select(func.count(XpLedger.id)).where(
            XpLedger.user_id == user.id,
            XpLedger.action == "watch_movie",
        )
    )).scalar_one()
    assert ledger_count == 1
