"""Pure-Python algorithmic trophies: ``secret_allnight``, ``secret_no_life``,
``secret_king``. All three checks reuse the existing
``playback_sessions`` table — no new data dependency — and rely on the
helpers in :mod:`services.portal.playback_algorithms`.

Each graduating trophy has at least one **functional unlock test** that
goes through ``check_all_achievements`` end-to-end, asserting on the
``user_achievements`` row rather than calling the helper in isolation.
The catalogue/placeholder check below is *not* a substitute — it only
verifies the seal was lifted.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from core.security import hash_password
from models.playback_stats import PlaybackSession
from models.portal.achievement import UserAchievement
from models.portal.profile import UserProfile
from models.user import User
from services.portal.achievement_defs_constants import PLACEHOLDER_IDS
from services.portal.achievements import (
    check_all_achievements,
    seed_achievements,
)


# ── Shared helpers ──────────────────────────────────────────────────────


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
        display_name=username.title(),
        role="viewer",
        account_active=True,
    ))
    await db.commit()
    return user


def _make_session(
    db,
    *,
    emby_user_id: str,
    user_name: str,
    item_id: str,
    started_at: datetime,
    ended_at: datetime | None,
    item_type: str = "Movie",
    suffix: str = "",
) -> None:
    """Insert one ``PlaybackSession`` row with the minimum fields the
    Python-algo helpers need. ``user_id`` is the **Emby user_id string**;
    ``user_name`` is what ``user_filter`` keys off."""
    db.add(PlaybackSession(
        session_key=f"sess-{user_name}-{item_id}-{int(started_at.timestamp())}-{suffix}",
        user_id=emby_user_id,
        user_name=user_name,
        item_id=item_id,
        item_name=f"Item {item_id}",
        item_type=item_type,
        library_name="Movies",
        started_at=started_at,
        last_seen_at=ended_at or started_at,
        ended_at=ended_at,
        is_active=ended_at is None,
    ))


async def _ach_unlocked(db, user_id: int, ach_id: str) -> bool:
    row = (await db.execute(
        select(UserAchievement).where(
            UserAchievement.user_id == user_id,
            UserAchievement.achievement_id == ach_id,
        )
    )).scalar_one_or_none()
    return bool(row and row.unlocked)


# ── secret_allnight ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_allnight_unlocks_with_continuous_session_22_to_06(db_session):
    alice = await _make_viewer(db_session, "alice")
    await seed_achievements(db_session)

    start = datetime(2026, 4, 10, 22, 0, tzinfo=timezone.utc)
    _make_session(
        db_session,
        emby_user_id="emby-alice",
        user_name=alice.username,
        item_id="movie-1",
        started_at=start,
        ended_at=start + timedelta(hours=8),
    )
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert await _ach_unlocked(db_session, alice.id, "secret_allnight")


@pytest.mark.asyncio
async def test_allnight_unlocks_with_chain_of_sessions_with_short_gaps(db_session):
    alice = await _make_viewer(db_session, "alice")
    await seed_achievements(db_session)

    base = datetime(2026, 4, 10, 22, 0, tzinfo=timezone.utc)
    # Session 1: 22:00 → 00:00 (2h)
    _make_session(
        db_session,
        emby_user_id="emby-alice",
        user_name=alice.username,
        item_id="movie-1",
        started_at=base,
        ended_at=base + timedelta(hours=2),
        suffix="a",
    )
    # 3-minute toilet break, then session 2: 00:03 → 03:00 (~3h)
    _make_session(
        db_session,
        emby_user_id="emby-alice",
        user_name=alice.username,
        item_id="movie-2",
        started_at=base + timedelta(hours=2, minutes=3),
        ended_at=base + timedelta(hours=5),
        suffix="b",
    )
    # 4-minute device handoff, then session 3: 03:04 → 06:10
    _make_session(
        db_session,
        emby_user_id="emby-alice",
        user_name=alice.username,
        item_id="movie-3",
        started_at=base + timedelta(hours=5, minutes=4),
        ended_at=base + timedelta(hours=8, minutes=10),
        suffix="c",
    )
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert await _ach_unlocked(db_session, alice.id, "secret_allnight")


@pytest.mark.asyncio
async def test_allnight_blocked_when_gap_exceeds_5min(db_session):
    alice = await _make_viewer(db_session, "alice")
    await seed_achievements(db_session)

    base = datetime(2026, 4, 10, 22, 0, tzinfo=timezone.utc)
    # 22:00 → 00:00, then 10-minute gap, then 00:10 → 06:05.
    _make_session(
        db_session,
        emby_user_id="emby-alice",
        user_name=alice.username,
        item_id="movie-1",
        started_at=base,
        ended_at=base + timedelta(hours=2),
        suffix="a",
    )
    _make_session(
        db_session,
        emby_user_id="emby-alice",
        user_name=alice.username,
        item_id="movie-2",
        started_at=base + timedelta(hours=2, minutes=10),
        ended_at=base + timedelta(hours=8, minutes=5),
        suffix="b",
    )
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert not await _ach_unlocked(db_session, alice.id, "secret_allnight")


@pytest.mark.asyncio
async def test_allnight_blocked_when_window_incomplete(db_session):
    """Starts at 23:00, ends at 04:00 — neither anchor (22:00 → 06:00) fits."""
    alice = await _make_viewer(db_session, "alice")
    await seed_achievements(db_session)

    start = datetime(2026, 4, 10, 23, 0, tzinfo=timezone.utc)
    _make_session(
        db_session,
        emby_user_id="emby-alice",
        user_name=alice.username,
        item_id="movie-1",
        started_at=start,
        ended_at=start + timedelta(hours=5),
    )
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert not await _ach_unlocked(db_session, alice.id, "secret_allnight")


@pytest.mark.asyncio
async def test_allnight_blocked_outside_22_06_window(db_session):
    """Daytime 8h binge (12:00 → 20:00) cannot satisfy the all-nighter window."""
    alice = await _make_viewer(db_session, "alice")
    await seed_achievements(db_session)

    start = datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc)
    _make_session(
        db_session,
        emby_user_id="emby-alice",
        user_name=alice.username,
        item_id="movie-1",
        started_at=start,
        ended_at=start + timedelta(hours=8),
    )
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert not await _ach_unlocked(db_session, alice.id, "secret_allnight")


# ── secret_no_life ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_no_life_unlocks_with_24h_in_48h_sliding_window(db_session):
    alice = await _make_viewer(db_session, "alice")
    await seed_achievements(db_session)

    base = datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)
    # 24 sessions of 1h each, started one per hour → 24h cumulative within
    # a 24h span (well inside the 48h sliding window).
    for i in range(24):
        _make_session(
            db_session,
            emby_user_id="emby-alice",
            user_name=alice.username,
            item_id=f"movie-{i}",
            started_at=base + timedelta(hours=i),
            ended_at=base + timedelta(hours=i + 1),
            suffix=str(i),
        )
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert await _ach_unlocked(db_session, alice.id, "secret_no_life")


@pytest.mark.asyncio
async def test_no_life_blocked_with_23h_55min_in_48h(db_session):
    alice = await _make_viewer(db_session, "alice")
    await seed_achievements(db_session)

    base = datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)
    # 23 sessions of 1h + 1 of 55 min, all packed into < 48h → 23h 55min total.
    for i in range(23):
        _make_session(
            db_session,
            emby_user_id="emby-alice",
            user_name=alice.username,
            item_id=f"movie-{i}",
            started_at=base + timedelta(hours=i),
            ended_at=base + timedelta(hours=i + 1),
            suffix=str(i),
        )
    short_start = base + timedelta(hours=23)
    _make_session(
        db_session,
        emby_user_id="emby-alice",
        user_name=alice.username,
        item_id="movie-short",
        started_at=short_start,
        ended_at=short_start + timedelta(minutes=55),
        suffix="short",
    )
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert not await _ach_unlocked(db_session, alice.id, "secret_no_life")


@pytest.mark.asyncio
async def test_no_life_blocked_when_24h_spread_over_72h(db_session):
    alice = await _make_viewer(db_session, "alice")
    await seed_achievements(db_session)

    base = datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)
    # 24 hour-long sessions spaced 3h apart → 72h span, no 48h window
    # ever holds more than 16h.
    for i in range(24):
        start = base + timedelta(hours=i * 3)
        _make_session(
            db_session,
            emby_user_id="emby-alice",
            user_name=alice.username,
            item_id=f"movie-{i}",
            started_at=start,
            ended_at=start + timedelta(hours=1),
            suffix=str(i),
        )
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert not await _ach_unlocked(db_session, alice.id, "secret_no_life")


# ── secret_king ─────────────────────────────────────────────────────────


def _month_start(year: int, month: int) -> datetime:
    # Avoid 12:00 UTC: it triggers the unrelated ``secret_gourmet`` lunch
    # window check, which has a preexisting SQLite-only bug when the test
    # produces >= 7 distinct noon dates.
    return datetime(year, month, 1, 14, 0, tzinfo=timezone.utc)


def _seed_alice_top_month(db, alice_username: str, year: int, month: int) -> None:
    """Alice 2h, Bob 1h: Alice wins this month and the N>=2 guard passes."""
    start = _month_start(year, month)
    _make_session(
        db,
        emby_user_id="emby-alice",
        user_name=alice_username,
        item_id=f"movie-alice-{year}-{month}",
        started_at=start,
        ended_at=start + timedelta(hours=2),
        suffix=f"alice-{year}-{month}",
    )
    _make_session(
        db,
        emby_user_id="emby-bob",
        user_name="bob",
        item_id=f"movie-bob-{year}-{month}",
        started_at=start + timedelta(hours=3),
        ended_at=start + timedelta(hours=4),
        suffix=f"bob-{year}-{month}",
    )


def _seed_bob_top_month(db, alice_username: str, year: int, month: int) -> None:
    """Bob 3h, Alice 1h: Bob wins this month."""
    start = _month_start(year, month)
    _make_session(
        db,
        emby_user_id="emby-alice",
        user_name=alice_username,
        item_id=f"movie-alice-{year}-{month}",
        started_at=start,
        ended_at=start + timedelta(hours=1),
        suffix=f"alice-{year}-{month}",
    )
    _make_session(
        db,
        emby_user_id="emby-bob",
        user_name="bob",
        item_id=f"movie-bob-{year}-{month}",
        started_at=start + timedelta(hours=2),
        ended_at=start + timedelta(hours=5),
        suffix=f"bob-{year}-{month}",
    )


def _seed_alice_only_month(db, alice_username: str, year: int, month: int) -> None:
    """Alice alone (single user) — month is skipped by the N>=2 guard."""
    start = _month_start(year, month)
    _make_session(
        db,
        emby_user_id="emby-alice",
        user_name=alice_username,
        item_id=f"movie-alice-only-{year}-{month}",
        started_at=start,
        ended_at=start + timedelta(hours=1),
        suffix=f"alice-only-{year}-{month}",
    )


def _iter_consecutive_months(start_year: int, start_month: int, count: int):
    year, month = start_year, start_month
    for _ in range(count):
        yield year, month
        month += 1
        if month > 12:
            month = 1
            year += 1


@pytest.mark.asyncio
async def test_king_unlocks_with_12_consecutive_top1_months(db_session):
    alice = await _make_viewer(db_session, "alice")
    await _make_viewer(db_session, "bob")
    await seed_achievements(db_session)

    for year, month in _iter_consecutive_months(2025, 1, 12):
        _seed_alice_top_month(db_session, alice.username, year, month)
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert await _ach_unlocked(db_session, alice.id, "secret_king")


@pytest.mark.asyncio
async def test_king_blocked_with_11_consecutive_months(db_session):
    alice = await _make_viewer(db_session, "alice")
    await _make_viewer(db_session, "bob")
    await seed_achievements(db_session)

    for year, month in _iter_consecutive_months(2025, 1, 11):
        _seed_alice_top_month(db_session, alice.username, year, month)
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert not await _ach_unlocked(db_session, alice.id, "secret_king")


@pytest.mark.asyncio
async def test_king_blocked_when_overtaken_one_month(db_session):
    """8 Alice-king months, 1 Bob-king month, 8 more Alice-king months —
    longest run is 8, well below the 12 required."""
    alice = await _make_viewer(db_session, "alice")
    await _make_viewer(db_session, "bob")
    await seed_achievements(db_session)

    months = list(_iter_consecutive_months(2024, 1, 17))
    for year, month in months[:8]:
        _seed_alice_top_month(db_session, alice.username, year, month)
    bob_year, bob_month = months[8]
    _seed_bob_top_month(db_session, alice.username, bob_year, bob_month)
    for year, month in months[9:]:
        _seed_alice_top_month(db_session, alice.username, year, month)
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert not await _ach_unlocked(db_session, alice.id, "secret_king")


@pytest.mark.asyncio
async def test_king_blocked_when_single_user_universe(db_session):
    """Anti-trivial guard: a single-user instance must not unlock the king
    even with 24+ months of dominant activity."""
    alice = await _make_viewer(db_session, "alice")
    await seed_achievements(db_session)

    for year, month in _iter_consecutive_months(2024, 1, 24):
        _seed_alice_only_month(db_session, alice.username, year, month)
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert not await _ach_unlocked(db_session, alice.id, "secret_king")


@pytest.mark.asyncio
async def test_king_chain_continues_through_months_skipped_by_n2_rule(db_session):
    """10 qualifying king months, then 2 single-user months (skipped, do not
    break the chain), then 2 qualifying king months → chain reaches 12."""
    alice = await _make_viewer(db_session, "alice")
    await _make_viewer(db_session, "bob")
    await seed_achievements(db_session)

    months = list(_iter_consecutive_months(2024, 1, 14))
    for year, month in months[:10]:
        _seed_alice_top_month(db_session, alice.username, year, month)
    for year, month in months[10:12]:
        _seed_alice_only_month(db_session, alice.username, year, month)
    for year, month in months[12:]:
        _seed_alice_top_month(db_session, alice.username, year, month)
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert await _ach_unlocked(db_session, alice.id, "secret_king")


# ── Placeholder set hygiene ─────────────────────────────────────────────


def test_placeholder_set_no_longer_seals_python_algo_family():
    for ach_id in ("secret_allnight", "secret_no_life", "secret_king"):
        assert ach_id not in PLACEHOLDER_IDS
