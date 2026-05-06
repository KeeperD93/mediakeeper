"""Pause/resume detection in the playback collector and the
``secret_pipi`` unlock that consumes the resulting events.

The collector helper :func:`_process_pause_events` is exercised in
isolation with a deterministic ``now`` so transitions can be asserted
without faking the rest of the polling loop. The functional unlock test
seeds five qualifying events and then runs ``check_all_achievements``
end-to-end so the catalogue, the secret-B pass and the runner all agree.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from core.security import hash_password
from models.playback_stats import PlaybackPauseEvent
from models.portal.achievement import UserAchievement
from models.portal.profile import UserProfile
from models.user import User
from services.portal.achievement_defs_constants import PLACEHOLDER_IDS
from services.portal.achievements import check_all_achievements, seed_achievements
from services.stats_collector.collect import _process_pause_events


def _session_payload(*, paused: bool, user_id: str = "EMBY-ALICE",
                     user_name: str = "Alice", item_id: str = "MOVIE-1",
                     session_id: str = "SESSION-1",
                     item_type: str = "Movie") -> dict:
    return {
        "Id": session_id,
        "UserId": user_id,
        "UserName": user_name,
        "PlayState": {"IsPaused": paused, "PositionTicks": 0},
        "NowPlayingItem": {
            "Id": item_id,
            "Name": "A Movie",
            "Type": item_type,
        },
    }


async def _open_count(db) -> int:
    res = await db.execute(
        select(PlaybackPauseEvent).where(PlaybackPauseEvent.resumed_at.is_(None))
    )
    return len(res.scalars().all())


async def _all_events(db) -> list[PlaybackPauseEvent]:
    res = await db.execute(select(PlaybackPauseEvent))
    return list(res.scalars().all())


# ── Collector helper: pause/resume transitions ──────────────────────────


@pytest.mark.asyncio
async def test_pause_event_created_then_closed_within_qualifying_window(db_session):
    base = datetime(2026, 5, 6, 20, 0, tzinfo=timezone.utc)

    await _process_pause_events(db_session, [_session_payload(paused=True)], base)
    await db_session.commit()
    assert await _open_count(db_session) == 1

    resume = base + timedelta(seconds=180)
    await _process_pause_events(db_session, [_session_payload(paused=False)], resume)
    await db_session.commit()

    events = await _all_events(db_session)
    assert len(events) == 1
    assert events[0].resumed_at is not None
    assert events[0].duration_seconds == 180


@pytest.mark.asyncio
async def test_pause_too_short_does_not_qualify(db_session):
    base = datetime(2026, 5, 6, 20, 0, tzinfo=timezone.utc)
    await _process_pause_events(db_session, [_session_payload(paused=True)], base)
    await _process_pause_events(
        db_session,
        [_session_payload(paused=False)],
        base + timedelta(seconds=60),
    )
    await db_session.commit()

    events = await _all_events(db_session)
    assert len(events) == 1
    assert events[0].duration_seconds == 60
    # 60s < 120s threshold → not qualifying for secret_pipi.


@pytest.mark.asyncio
async def test_pause_too_long_does_not_qualify(db_session):
    base = datetime(2026, 5, 6, 20, 0, tzinfo=timezone.utc)
    await _process_pause_events(db_session, [_session_payload(paused=True)], base)
    await _process_pause_events(
        db_session,
        [_session_payload(paused=False)],
        base + timedelta(seconds=600),
    )
    await db_session.commit()

    events = await _all_events(db_session)
    assert len(events) == 1
    assert events[0].duration_seconds == 600
    # 600s > 300s threshold → not qualifying for secret_pipi.


@pytest.mark.asyncio
async def test_repeated_paused_ticks_do_not_create_duplicate_events(db_session):
    base = datetime(2026, 5, 6, 20, 0, tzinfo=timezone.utc)
    payload = _session_payload(paused=True)

    await _process_pause_events(db_session, [payload], base)
    await db_session.commit()
    await _process_pause_events(db_session, [payload], base + timedelta(seconds=15))
    await db_session.commit()
    await _process_pause_events(db_session, [payload], base + timedelta(seconds=30))
    await db_session.commit()

    events = await _all_events(db_session)
    assert len(events) == 1
    assert events[0].resumed_at is None


@pytest.mark.asyncio
async def test_repeated_playing_ticks_do_not_re_close_event(db_session):
    base = datetime(2026, 5, 6, 20, 0, tzinfo=timezone.utc)

    await _process_pause_events(db_session, [_session_payload(paused=True)], base)
    await db_session.commit()
    resume = base + timedelta(seconds=180)
    await _process_pause_events(db_session, [_session_payload(paused=False)], resume)
    await db_session.commit()

    events = await _all_events(db_session)
    assert len(events) == 1
    first_resumed_at = events[0].resumed_at
    first_duration = events[0].duration_seconds

    await _process_pause_events(
        db_session,
        [_session_payload(paused=False)],
        resume + timedelta(seconds=120),
    )
    await db_session.commit()

    events = await _all_events(db_session)
    assert len(events) == 1
    assert events[0].resumed_at == first_resumed_at
    assert events[0].duration_seconds == first_duration


@pytest.mark.asyncio
async def test_disappeared_session_without_resume_stays_open(db_session):
    base = datetime(2026, 5, 6, 20, 0, tzinfo=timezone.utc)

    await _process_pause_events(db_session, [_session_payload(paused=True)], base)
    await db_session.commit()
    # Next poll: session disappeared (Emby returns nothing for that key).
    await _process_pause_events(db_session, [], base + timedelta(seconds=30))
    await db_session.commit()

    events = await _all_events(db_session)
    assert len(events) == 1
    assert events[0].resumed_at is None
    assert events[0].duration_seconds is None
    # Open events never count toward secret_pipi (resumed_at IS NOT NULL filter).


# ── Catalogue check ─────────────────────────────────────────────────────


def test_secret_pipi_no_longer_in_placeholder_ids():
    assert "secret_pipi" not in PLACEHOLDER_IDS


# ── Functional unlock ───────────────────────────────────────────────────


async def _make_viewer(db, username: str) -> User:
    user = User(
        username=username,
        hashed_password=hash_password("ViewerPassword123!"),
        is_active=True,
        must_change_password=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    db.add(UserProfile(
        user_id=user.id,
        display_name=username,
        role="viewer",
        account_active=True,
        emby_user_id="EMBY-PIPI",
    ))
    await db.commit()
    return user


@pytest.mark.asyncio
async def test_secret_pipi_unlocks_with_5_qualifying_pause_events(db_session):
    alice = await _make_viewer(db_session, "alice")
    await seed_achievements(db_session)

    base = datetime(2026, 5, 6, 20, 0, tzinfo=timezone.utc)
    for i in range(5):
        pause_started = base + timedelta(hours=i)
        db_session.add(PlaybackPauseEvent(
            session_key=f"EMBY-PIPI_MOVIE-{i}_SESSION-{i}",
            emby_session_id=f"SESSION-{i}",
            user_id="EMBY-PIPI",
            user_name=alice.username,
            item_id=f"MOVIE-{i}",
            item_name=f"Movie {i}",
            item_type="Movie",
            pause_started_at=pause_started,
            resumed_at=pause_started + timedelta(seconds=180),
            duration_seconds=180,
        ))
    await db_session.commit()

    unlocks = await check_all_achievements(db_session, alice.id, alice.username)
    unlock_ids = {u.get("achievement_id") or u.get("id") for u in unlocks}
    assert "secret_pipi" in unlock_ids

    row = (await db_session.execute(
        select(UserAchievement).where(
            UserAchievement.user_id == alice.id,
            UserAchievement.achievement_id == "secret_pipi",
        )
    )).scalar_one_or_none()
    assert row is not None
    assert row.unlocked is True


@pytest.mark.asyncio
async def test_secret_pipi_does_not_unlock_with_4_qualifying_events(db_session):
    alice = await _make_viewer(db_session, "alice")
    await seed_achievements(db_session)

    base = datetime(2026, 5, 6, 20, 0, tzinfo=timezone.utc)
    for i in range(4):
        pause_started = base + timedelta(hours=i)
        db_session.add(PlaybackPauseEvent(
            session_key=f"EMBY-PIPI_MOVIE-{i}_SESSION-{i}",
            emby_session_id=f"SESSION-{i}",
            user_id="EMBY-PIPI",
            user_name=alice.username,
            item_id=f"MOVIE-{i}",
            item_name=f"Movie {i}",
            item_type="Movie",
            pause_started_at=pause_started,
            resumed_at=pause_started + timedelta(seconds=180),
            duration_seconds=180,
        ))
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    row = (await db_session.execute(
        select(UserAchievement).where(
            UserAchievement.user_id == alice.id,
            UserAchievement.achievement_id == "secret_pipi",
        )
    )).scalar_one_or_none()
    assert row is None or row.unlocked is False


@pytest.mark.asyncio
async def test_secret_pipi_ignores_open_and_out_of_range_events(db_session):
    alice = await _make_viewer(db_session, "alice")
    await seed_achievements(db_session)

    base = datetime(2026, 5, 6, 20, 0, tzinfo=timezone.utc)
    # 3 qualifying (180s) + 2 open + 2 too short (60s) + 2 too long (600s).
    payloads = [
        (180, True),  (180, True),  (180, True),
        (None, None), (None, None),
        (60, True),   (60, True),
        (600, True),  (600, True),
    ]
    for i, (duration, qualifying) in enumerate(payloads):
        pause_started = base + timedelta(hours=i)
        if duration is None:
            resumed_at = None
        else:
            resumed_at = pause_started + timedelta(seconds=duration)
        db_session.add(PlaybackPauseEvent(
            session_key=f"EMBY-PIPI_MOVIE-{i}_SESSION-{i}",
            user_id="EMBY-PIPI",
            user_name=alice.username,
            item_id=f"MOVIE-{i}",
            item_name=f"Movie {i}",
            item_type="Movie",
            pause_started_at=pause_started,
            resumed_at=resumed_at,
            duration_seconds=duration,
        ))
        # Silence the unused name; keeps the structure declarative.
        _ = qualifying
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    row = (await db_session.execute(
        select(UserAchievement).where(
            UserAchievement.user_id == alice.id,
            UserAchievement.achievement_id == "secret_pipi",
        )
    )).scalar_one_or_none()
    assert row is None or row.unlocked is False
