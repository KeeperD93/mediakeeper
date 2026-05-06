"""Pause/resume detection in the playback collector and the
``secret_pipi`` unlock that consumes the resulting events.

The collector helper :func:`_process_pause_events` is exercised in
isolation with a deterministic ``now`` so transitions can be asserted
without faking the rest of the polling loop. Every paused-tick test
seeds a recent-active ``PlaybackSession`` first because the helper
requires fresh proof of playing before opening a new pause event (the
cold-start guard). The functional unlock test seeds five qualifying
events and runs ``check_all_achievements`` end-to-end so the catalogue,
the secret-B pass and the runner all agree.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from core.security import hash_password
from models.playback_stats import PlaybackPauseEvent, PlaybackSession
from models.portal.achievement import UserAchievement
from models.portal.profile import UserProfile
from models.user import User
from services.portal.achievement_defs_constants import PLACEHOLDER_IDS
from services.portal.achievements import check_all_achievements, seed_achievements
from services.settings import set_setting
from services.stats_collector.collect import _process_pause_events


def _session_payload(*, paused: bool, user_id: str = "EMBY-ALICE",
                     user_name: str = "Alice", item_id: str = "MOVIE-1",
                     session_id: str = "SESSION-1",
                     item_type: str = "Movie",
                     item_name: str = "A Movie") -> dict:
    return {
        "Id": session_id,
        "UserId": user_id,
        "UserName": user_name,
        "PlayState": {"IsPaused": paused, "PositionTicks": 0},
        "NowPlayingItem": {
            "Id": item_id,
            "Name": item_name,
            "Type": item_type,
        },
    }


def _session_key(payload: dict) -> str:
    np = payload["NowPlayingItem"]
    return f"{payload['UserId']}_{np['Id']}_{payload['Id']}"


async def _seed_active_session(
    db, payload: dict, *, last_seen_at: datetime, started_at: datetime | None = None,
) -> PlaybackSession:
    """Insert the ``PlaybackSession`` row that ``_process_pause_events``
    requires as proof of recent playing before opening a pause event."""
    np = payload["NowPlayingItem"]
    row = PlaybackSession(
        session_key=_session_key(payload),
        user_id=payload["UserId"],
        user_name=payload["UserName"],
        item_id=np["Id"],
        item_name=np["Name"],
        item_type=np["Type"],
        started_at=started_at or last_seen_at,
        last_seen_at=last_seen_at,
        is_active=True,
    )
    db.add(row)
    await db.commit()
    return row


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
    payload_paused = _session_payload(paused=True)
    payload_playing = _session_payload(paused=False)
    await _seed_active_session(db_session, payload_paused, last_seen_at=base)

    pause_at = base + timedelta(seconds=15)
    await _process_pause_events(db_session, [payload_paused], pause_at)
    await db_session.commit()
    assert await _open_count(db_session) == 1

    resume = pause_at + timedelta(seconds=180)
    await _process_pause_events(db_session, [payload_playing], resume)
    await db_session.commit()

    events = await _all_events(db_session)
    assert len(events) == 1
    assert events[0].resumed_at is not None
    assert events[0].duration_seconds == 180


@pytest.mark.asyncio
async def test_pause_too_short_does_not_qualify(db_session):
    base = datetime(2026, 5, 6, 20, 0, tzinfo=timezone.utc)
    payload_paused = _session_payload(paused=True)
    payload_playing = _session_payload(paused=False)
    await _seed_active_session(db_session, payload_paused, last_seen_at=base)

    await _process_pause_events(db_session, [payload_paused], base)
    await _process_pause_events(
        db_session, [payload_playing], base + timedelta(seconds=60),
    )
    await db_session.commit()

    events = await _all_events(db_session)
    assert len(events) == 1
    assert events[0].duration_seconds == 60
    # 60s < 120s threshold → not qualifying for secret_pipi.


@pytest.mark.asyncio
async def test_pause_too_long_does_not_qualify(db_session):
    base = datetime(2026, 5, 6, 20, 0, tzinfo=timezone.utc)
    payload_paused = _session_payload(paused=True)
    payload_playing = _session_payload(paused=False)
    await _seed_active_session(db_session, payload_paused, last_seen_at=base)

    await _process_pause_events(db_session, [payload_paused], base)
    await _process_pause_events(
        db_session, [payload_playing], base + timedelta(seconds=600),
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
    await _seed_active_session(db_session, payload, last_seen_at=base)

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
    payload_paused = _session_payload(paused=True)
    payload_playing = _session_payload(paused=False)
    await _seed_active_session(db_session, payload_paused, last_seen_at=base)

    await _process_pause_events(db_session, [payload_paused], base)
    await db_session.commit()
    resume = base + timedelta(seconds=180)
    await _process_pause_events(db_session, [payload_playing], resume)
    await db_session.commit()

    events = await _all_events(db_session)
    assert len(events) == 1
    first_resumed_at = events[0].resumed_at
    first_duration = events[0].duration_seconds

    await _process_pause_events(
        db_session, [payload_playing], resume + timedelta(seconds=120),
    )
    await db_session.commit()

    events = await _all_events(db_session)
    assert len(events) == 1
    assert events[0].resumed_at == first_resumed_at
    assert events[0].duration_seconds == first_duration


@pytest.mark.asyncio
async def test_disappeared_session_without_resume_stays_open(db_session):
    base = datetime(2026, 5, 6, 20, 0, tzinfo=timezone.utc)
    payload_paused = _session_payload(paused=True)
    await _seed_active_session(db_session, payload_paused, last_seen_at=base)

    await _process_pause_events(db_session, [payload_paused], base)
    await db_session.commit()
    # Next poll: session disappeared (Emby returns nothing for that key).
    await _process_pause_events(db_session, [], base + timedelta(seconds=30))
    await db_session.commit()

    events = await _all_events(db_session)
    assert len(events) == 1
    assert events[0].resumed_at is None
    assert events[0].duration_seconds is None
    # Open events never count toward secret_pipi (resumed_at IS NOT NULL filter).


# ── Cold-start guard ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pause_normal_flow_after_playing_tick_creates_event(db_session):
    """Regression: a paused tick observed shortly after a playing tick
    must still open and close a qualifying event end to end."""
    base = datetime(2026, 5, 6, 20, 0, tzinfo=timezone.utc)
    payload_paused = _session_payload(paused=True)
    payload_playing = _session_payload(paused=False)

    await _seed_active_session(db_session, payload_paused, last_seen_at=base)

    await _process_pause_events(
        db_session, [payload_paused], base + timedelta(seconds=15),
    )
    await db_session.commit()
    await _process_pause_events(
        db_session, [payload_playing], base + timedelta(seconds=195),
    )
    await db_session.commit()

    events = await _all_events(db_session)
    assert len(events) == 1
    assert events[0].duration_seconds == 180


@pytest.mark.asyncio
async def test_cold_start_paused_without_existing_session_does_not_open(db_session):
    """If the collector observes a paused tick on a session_key with no
    matching ``PlaybackSession`` row at all, no pause event is opened."""
    base = datetime(2026, 5, 6, 20, 0, tzinfo=timezone.utc)
    payload_paused = _session_payload(paused=True)

    await _process_pause_events(db_session, [payload_paused], base)
    await db_session.commit()

    assert await _all_events(db_session) == []


@pytest.mark.asyncio
async def test_stale_active_row_does_not_open_pause_event(db_session):
    """An active ``PlaybackSession`` row whose ``last_seen_at`` is older
    than the proof window must NOT count as fresh playing evidence."""
    now = datetime(2026, 5, 6, 20, 0, tzinfo=timezone.utc)
    payload_paused = _session_payload(paused=True)
    await _seed_active_session(
        db_session, payload_paused, last_seen_at=now - timedelta(minutes=10),
    )

    await _process_pause_events(db_session, [payload_paused], now)
    await db_session.commit()

    assert await _all_events(db_session) == []


# ── Catalogue check ─────────────────────────────────────────────────────


def test_secret_pipi_no_longer_in_placeholder_ids():
    assert "secret_pipi" not in PLACEHOLDER_IDS


# ── Functional unlock + exclusions ──────────────────────────────────────


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


def _qualifying_event(*, user_name: str, idx: int, item_name: str,
                      base: datetime) -> PlaybackPauseEvent:
    pause_started = base + timedelta(hours=idx)
    return PlaybackPauseEvent(
        session_key=f"EMBY-PIPI_MOVIE-{idx}_SESSION-{idx}",
        emby_session_id=f"SESSION-{idx}",
        user_id="EMBY-PIPI",
        user_name=user_name,
        item_id=f"MOVIE-{idx}",
        item_name=item_name,
        item_type="Movie",
        pause_started_at=pause_started,
        resumed_at=pause_started + timedelta(seconds=180),
        duration_seconds=180,
    )


async def _is_unlocked(db, user_id: int, ach_id: str) -> bool:
    row = (await db.execute(
        select(UserAchievement).where(
            UserAchievement.user_id == user_id,
            UserAchievement.achievement_id == ach_id,
        )
    )).scalar_one_or_none()
    return bool(row and row.unlocked)


@pytest.mark.asyncio
async def test_secret_pipi_unlocks_with_5_qualifying_pause_events(db_session):
    alice = await _make_viewer(db_session, "alice")
    await seed_achievements(db_session)

    base = datetime(2026, 5, 6, 20, 0, tzinfo=timezone.utc)
    for i in range(5):
        db_session.add(_qualifying_event(
            user_name=alice.username, idx=i, item_name=f"Movie {i}", base=base,
        ))
    await db_session.commit()

    unlocks = await check_all_achievements(db_session, alice.id, alice.username)
    unlock_ids = {u.get("achievement_id") or u.get("id") for u in unlocks}
    assert "secret_pipi" in unlock_ids
    assert await _is_unlocked(db_session, alice.id, "secret_pipi")


@pytest.mark.asyncio
async def test_secret_pipi_does_not_unlock_with_4_qualifying_events(db_session):
    alice = await _make_viewer(db_session, "alice")
    await seed_achievements(db_session)

    base = datetime(2026, 5, 6, 20, 0, tzinfo=timezone.utc)
    for i in range(4):
        db_session.add(_qualifying_event(
            user_name=alice.username, idx=i, item_name=f"Movie {i}", base=base,
        ))
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert not await _is_unlocked(db_session, alice.id, "secret_pipi")


@pytest.mark.asyncio
async def test_secret_pipi_ignores_open_and_out_of_range_events(db_session):
    alice = await _make_viewer(db_session, "alice")
    await seed_achievements(db_session)

    base = datetime(2026, 5, 6, 20, 0, tzinfo=timezone.utc)
    # 3 qualifying (180s) + 2 open + 2 too short (60s) + 2 too long (600s).
    payloads = [180, 180, 180, None, None, 60, 60, 600, 600]
    for i, duration in enumerate(payloads):
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
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert not await _is_unlocked(db_session, alice.id, "secret_pipi")


@pytest.mark.asyncio
async def test_secret_pipi_skips_excluded_item_name(db_session):
    """5 qualifying pauses on an item blacklisted via stats.exclusions
    must NOT unlock the trophy."""
    alice = await _make_viewer(db_session, "alice")
    await seed_achievements(db_session)
    await set_setting(
        db_session, "stats.exclusions",
        json.dumps([{"mode": "exact", "value": "Excluded Theme"}]),
    )

    base = datetime(2026, 5, 6, 20, 0, tzinfo=timezone.utc)
    for i in range(5):
        db_session.add(_qualifying_event(
            user_name=alice.username, idx=i,
            item_name="Excluded Theme", base=base,
        ))
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert not await _is_unlocked(db_session, alice.id, "secret_pipi")


@pytest.mark.asyncio
async def test_secret_pipi_mixed_exclusion_below_threshold_no_unlock(db_session):
    """4 qualifying non-excluded events + 1 excluded event = below
    threshold; the excluded one is filtered out."""
    alice = await _make_viewer(db_session, "alice")
    await seed_achievements(db_session)
    await set_setting(
        db_session, "stats.exclusions",
        json.dumps([{"mode": "exact", "value": "Excluded Theme"}]),
    )

    base = datetime(2026, 5, 6, 20, 0, tzinfo=timezone.utc)
    for i in range(4):
        db_session.add(_qualifying_event(
            user_name=alice.username, idx=i,
            item_name=f"Movie {i}", base=base,
        ))
    db_session.add(_qualifying_event(
        user_name=alice.username, idx=99,
        item_name="Excluded Theme", base=base,
    ))
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert not await _is_unlocked(db_session, alice.id, "secret_pipi")


@pytest.mark.asyncio
async def test_secret_pipi_unlocks_with_5_non_excluded_events_alongside_exclusions(
    db_session,
):
    """Regression: 5 qualifying non-excluded events still unlock the
    trophy when the exclusions list is configured."""
    alice = await _make_viewer(db_session, "alice")
    await seed_achievements(db_session)
    await set_setting(
        db_session, "stats.exclusions",
        json.dumps([{"mode": "exact", "value": "Excluded Theme"}]),
    )

    base = datetime(2026, 5, 6, 20, 0, tzinfo=timezone.utc)
    for i in range(5):
        db_session.add(_qualifying_event(
            user_name=alice.username, idx=i,
            item_name=f"Movie {i}", base=base,
        ))
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert await _is_unlocked(db_session, alice.id, "secret_pipi")
