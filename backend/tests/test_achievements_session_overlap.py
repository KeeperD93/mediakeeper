"""Cross-user concurrency trophies: ``secret_lonely`` and ``secret_sync``.

Both checks read from the same ``playback_sessions`` table the rest of
the achievements pipeline already trusts — no new data dependency. The
tests cover:

* the loner unlocks on a NYE session with no overlapping other-user
  session, and stays locked when the overlap exists or the session is
  outside the Dec 31 / Jan 1 window,
* the in-sync unlocks when another user's session overlaps the same
  ``item_id`` and stays locked when the windows are disjoint or the
  binge is the same MK user on two devices,
* the anti-trivial guard returns 0 on a single-user instance for both
  trophies regardless of how good the technical match looks,
* the placeholder set no longer seals this family.
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


# ── Helpers ─────────────────────────────────────────────────────────────


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
) -> None:
    """Insert one ``PlaybackSession`` row with the minimum fields the
    overlap helpers need. ``user_id`` is the **Emby user_id string**;
    ``user_name`` is what ``user_filter`` keys off."""
    db.add(PlaybackSession(
        session_key=f"sess-{user_name}-{item_id}-{int(started_at.timestamp())}",
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


# ── 1. secret_lonely happy path ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_secret_lonely_unlocks_when_alone_on_nye(db_session):
    alice = await _make_viewer(db_session, "alice")
    await _make_viewer(db_session, "bob")
    await seed_achievements(db_session)

    nye = datetime(2025, 12, 31, 22, 0, tzinfo=timezone.utc)
    _make_session(
        db_session,
        emby_user_id="emby-alice",
        user_name=alice.username,
        item_id="movie-1",
        started_at=nye,
        ended_at=nye + timedelta(hours=2),
    )
    # Bob has activity but nowhere near alice's NYE window — no overlap.
    _make_session(
        db_session,
        emby_user_id="emby-bob",
        user_name="bob",
        item_id="movie-2",
        started_at=datetime(2025, 7, 15, 14, 0, tzinfo=timezone.utc),
        ended_at=datetime(2025, 7, 15, 16, 0, tzinfo=timezone.utc),
    )
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert await _ach_unlocked(db_session, alice.id, "secret_lonely")


# ── 2. secret_lonely blocked by overlap ─────────────────────────────────


@pytest.mark.asyncio
async def test_secret_lonely_blocked_when_overlap_exists(db_session):
    alice = await _make_viewer(db_session, "alice")
    await _make_viewer(db_session, "bob")
    await seed_achievements(db_session)

    nye = datetime(2025, 12, 31, 22, 0, tzinfo=timezone.utc)
    _make_session(
        db_session,
        emby_user_id="emby-alice",
        user_name=alice.username,
        item_id="movie-1",
        started_at=nye,
        ended_at=nye + timedelta(hours=2),
    )
    # Bob's session overlaps alice's NYE window.
    _make_session(
        db_session,
        emby_user_id="emby-bob",
        user_name="bob",
        item_id="movie-bob",
        started_at=nye + timedelta(minutes=30),
        ended_at=nye + timedelta(hours=1, minutes=30),
    )
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert not await _ach_unlocked(db_session, alice.id, "secret_lonely")


# ── 3. secret_lonely outside NYE window ─────────────────────────────────


@pytest.mark.asyncio
async def test_secret_lonely_blocked_outside_nye_dates(db_session):
    alice = await _make_viewer(db_session, "alice")
    await _make_viewer(db_session, "bob")
    await seed_achievements(db_session)

    summer = datetime(2025, 7, 15, 22, 0, tzinfo=timezone.utc)
    _make_session(
        db_session,
        emby_user_id="emby-alice",
        user_name=alice.username,
        item_id="movie-1",
        started_at=summer,
        ended_at=summer + timedelta(hours=2),
    )
    # Bob exists (so the universe has 2 distinct users) but never
    # overlaps — yet the date itself is wrong, so no unlock.
    _make_session(
        db_session,
        emby_user_id="emby-bob",
        user_name="bob",
        item_id="movie-2",
        started_at=datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc),
    )
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert not await _ach_unlocked(db_session, alice.id, "secret_lonely")


# ── 4. secret_lonely anti-trivial guard ─────────────────────────────────


@pytest.mark.asyncio
async def test_secret_lonely_blocked_when_single_user_universe(db_session):
    alice = await _make_viewer(db_session, "alice")
    await seed_achievements(db_session)

    nye = datetime(2025, 12, 31, 22, 0, tzinfo=timezone.utc)
    _make_session(
        db_session,
        emby_user_id="emby-alice",
        user_name=alice.username,
        item_id="movie-1",
        started_at=nye,
        ended_at=nye + timedelta(hours=2),
    )
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert not await _ach_unlocked(db_session, alice.id, "secret_lonely")


# ── 5. secret_sync happy path ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_secret_sync_unlocks_with_overlap_other_user(db_session):
    alice = await _make_viewer(db_session, "alice")
    await _make_viewer(db_session, "bob")
    await seed_achievements(db_session)

    base = datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc)
    _make_session(
        db_session,
        emby_user_id="emby-alice",
        user_name=alice.username,
        item_id="movie-shared",
        started_at=base,
        ended_at=base + timedelta(hours=2),
    )
    _make_session(
        db_session,
        emby_user_id="emby-bob",
        user_name="bob",
        item_id="movie-shared",
        started_at=base + timedelta(minutes=15),
        ended_at=base + timedelta(hours=1, minutes=45),
    )
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert await _ach_unlocked(db_session, alice.id, "secret_sync")


# ── 6. secret_sync disjoint windows ─────────────────────────────────────


@pytest.mark.asyncio
async def test_secret_sync_blocked_without_overlap(db_session):
    alice = await _make_viewer(db_session, "alice")
    await _make_viewer(db_session, "bob")
    await seed_achievements(db_session)

    _make_session(
        db_session,
        emby_user_id="emby-alice",
        user_name=alice.username,
        item_id="movie-shared",
        started_at=datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 4, 10, 22, 0, tzinfo=timezone.utc),
    )
    _make_session(
        db_session,
        emby_user_id="emby-bob",
        user_name="bob",
        item_id="movie-shared",
        started_at=datetime(2026, 4, 11, 9, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 4, 11, 11, 0, tzinfo=timezone.utc),
    )
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert not await _ach_unlocked(db_session, alice.id, "secret_sync")


# ── 7. secret_sync anti-trivial guard ───────────────────────────────────


@pytest.mark.asyncio
async def test_secret_sync_blocked_when_single_user_universe(db_session):
    alice = await _make_viewer(db_session, "alice")
    await seed_achievements(db_session)

    base = datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc)
    _make_session(
        db_session,
        emby_user_id="emby-alice",
        user_name=alice.username,
        item_id="movie-shared",
        started_at=base,
        ended_at=base + timedelta(hours=2),
    )
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert not await _ach_unlocked(db_session, alice.id, "secret_sync")


# ── 8. secret_sync ignores same-user multi-device binge ─────────────────


@pytest.mark.asyncio
async def test_secret_sync_blocked_when_same_user_self_join(db_session):
    """Alice on TV + Alice on phone watching the same movie at the same
    time must not unlock In Sync — both rows share her Emby user_id."""
    alice = await _make_viewer(db_session, "alice")
    await _make_viewer(db_session, "bob")
    await seed_achievements(db_session)

    base = datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc)
    # Alice TV
    db_session.add(PlaybackSession(
        session_key="sess-alice-tv",
        user_id="emby-alice",
        user_name=alice.username,
        item_id="movie-shared",
        item_name="Item movie-shared",
        item_type="Movie",
        device_name="TV",
        library_name="Movies",
        started_at=base,
        last_seen_at=base + timedelta(hours=2),
        ended_at=base + timedelta(hours=2),
        is_active=False,
    ))
    # Alice phone — same Emby user_id, overlapping window.
    db_session.add(PlaybackSession(
        session_key="sess-alice-phone",
        user_id="emby-alice",
        user_name=alice.username,
        item_id="movie-shared",
        item_name="Item movie-shared",
        item_type="Movie",
        device_name="Phone",
        library_name="Movies",
        started_at=base + timedelta(minutes=10),
        last_seen_at=base + timedelta(hours=1, minutes=30),
        ended_at=base + timedelta(hours=1, minutes=30),
        is_active=False,
    ))
    # Bob exists in the DB to satisfy the anti-trivial guard, but does
    # NOT touch ``movie-shared`` so In Sync truly depends on the
    # cross-user same-item join.
    _make_session(
        db_session,
        emby_user_id="emby-bob",
        user_name="bob",
        item_id="movie-bob-only",
        started_at=datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 5, 1, 13, 0, tzinfo=timezone.utc),
    )
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert not await _ach_unlocked(db_session, alice.id, "secret_sync")


# ── 9. Placeholder set no longer seals the overlap family ───────────────


def test_placeholder_set_no_longer_seals_overlap_family():
    for ach_id in ("secret_lonely", "secret_sync"):
        assert ach_id not in PLACEHOLDER_IDS
