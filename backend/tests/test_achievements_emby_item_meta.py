"""Emby-metadata trophies: ``secret_pilot`` and ``secret_late``.

Both checks consume the new ``date_created`` column on
``emby_tmdb_index`` (cached straight from Emby's
``/Items?Fields=DateCreated``) — no TMDB key required.

Tests cover:
* ``secret_pilot`` unlock when the observed user is the first viewer
  inside the freshness window (``PILOT_FRESHNESS_DAYS``),
* ``secret_pilot`` blocked by an earlier other-user session, by an
  out-of-window timestamp, by missing ``date_created`` metadata, and
  by the single-user-instance anti-trivial guard,
* ``secret_late`` unlock when the session is at least 365 days after
  the file was added,
* ``secret_late`` blocked when the gap is shorter or the metadata is
  missing,
* the placeholder set no longer seals this family.

Each graduating trophy has at least one functional unlock test that
goes through ``check_all_achievements`` end-to-end — the catalogue
hygiene assertion at the bottom is not a substitute.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from core.security import hash_password
from models.playback_stats import PlaybackSession
from models.portal.achievement import UserAchievement
from models.portal.emby_tmdb_index import EmbyTmdbIndex
from models.portal.profile import UserProfile
from models.user import User
from services.portal.achievement_defs_constants import PLACEHOLDER_IDS
from services.portal.achievements import (
    check_all_achievements,
    seed_achievements,
)
from services.portal.playback_algorithms import PILOT_FRESHNESS_DAYS


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
    ended_at: datetime | None = None,
    item_type: str = "Movie",
    suffix: str = "",
) -> None:
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


def _index_row(
    db,
    *,
    item_id: str,
    date_created: datetime | None,
    media_type: str = "movie",
) -> None:
    db.add(EmbyTmdbIndex(
        emby_item_id=item_id,
        tmdb_id=hash(item_id) % 1_000_000,
        media_type=media_type,
        title=f"Item {item_id}",
        date_created=date_created,
    ))


async def _ach_unlocked(db, user_id: int, ach_id: str) -> bool:
    row = (await db.execute(
        select(UserAchievement).where(
            UserAchievement.user_id == user_id,
            UserAchievement.achievement_id == ach_id,
        )
    )).scalar_one_or_none()
    return bool(row and row.unlocked)


# ── secret_pilot ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pilot_unlocks_when_first_viewer_on_fresh_content(db_session):
    alice = await _make_viewer(db_session, "alice")
    await _make_viewer(db_session, "bob")
    await seed_achievements(db_session)

    now = datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc)
    created = now - timedelta(days=5)
    _index_row(db_session, item_id="movie-fresh", date_created=created)
    # Bob has a session on a *different* item so the universe is N>=2,
    # but Alice is the only one to have seen the fresh item.
    _make_session(
        db_session,
        emby_user_id="emby-bob",
        user_name="bob",
        item_id="movie-other",
        started_at=now - timedelta(days=10),
        ended_at=now - timedelta(days=10) + timedelta(hours=1),
        suffix="bob-other",
    )
    _make_session(
        db_session,
        emby_user_id="emby-alice",
        user_name=alice.username,
        item_id="movie-fresh",
        started_at=now,
        ended_at=now + timedelta(hours=1),
        suffix="alice-fresh",
    )
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert await _ach_unlocked(db_session, alice.id, "secret_pilot")


@pytest.mark.asyncio
async def test_pilot_blocked_when_not_first_viewer(db_session):
    alice = await _make_viewer(db_session, "alice")
    await _make_viewer(db_session, "bob")
    await seed_achievements(db_session)

    now = datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc)
    created = now - timedelta(days=3)
    _index_row(db_session, item_id="movie-fresh", date_created=created)
    # Bob saw the item 1 hour before Alice.
    _make_session(
        db_session,
        emby_user_id="emby-bob",
        user_name="bob",
        item_id="movie-fresh",
        started_at=now - timedelta(hours=1),
        ended_at=now,
        suffix="bob",
    )
    _make_session(
        db_session,
        emby_user_id="emby-alice",
        user_name=alice.username,
        item_id="movie-fresh",
        started_at=now,
        ended_at=now + timedelta(hours=1),
        suffix="alice",
    )
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert not await _ach_unlocked(db_session, alice.id, "secret_pilot")


@pytest.mark.asyncio
async def test_pilot_blocked_when_content_not_fresh(db_session):
    alice = await _make_viewer(db_session, "alice")
    await _make_viewer(db_session, "bob")
    await seed_achievements(db_session)

    now = datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc)
    # Item was added 60 days ago — well outside PILOT_FRESHNESS_DAYS.
    created = now - timedelta(days=PILOT_FRESHNESS_DAYS + 30)
    _index_row(db_session, item_id="movie-old", date_created=created)
    _make_session(
        db_session,
        emby_user_id="emby-bob",
        user_name="bob",
        item_id="movie-other",
        started_at=now - timedelta(days=10),
        ended_at=now - timedelta(days=10) + timedelta(hours=1),
        suffix="bob",
    )
    _make_session(
        db_session,
        emby_user_id="emby-alice",
        user_name=alice.username,
        item_id="movie-old",
        started_at=now,
        ended_at=now + timedelta(hours=1),
        suffix="alice",
    )
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert not await _ach_unlocked(db_session, alice.id, "secret_pilot")


@pytest.mark.asyncio
async def test_pilot_blocked_when_date_created_null(db_session):
    """No index row → no metadata → pilot cannot fire even if Alice is the
    sole viewer. The trophy demands a *proven* freshness claim."""
    alice = await _make_viewer(db_session, "alice")
    await _make_viewer(db_session, "bob")
    await seed_achievements(db_session)

    now = datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc)
    _make_session(
        db_session,
        emby_user_id="emby-bob",
        user_name="bob",
        item_id="movie-other",
        started_at=now - timedelta(days=10),
        ended_at=now - timedelta(days=10) + timedelta(hours=1),
        suffix="bob",
    )
    _make_session(
        db_session,
        emby_user_id="emby-alice",
        user_name=alice.username,
        item_id="movie-no-meta",
        started_at=now,
        ended_at=now + timedelta(hours=1),
        suffix="alice",
    )
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert not await _ach_unlocked(db_session, alice.id, "secret_pilot")


@pytest.mark.asyncio
async def test_pilot_blocked_when_single_user_universe(db_session):
    """Anti-trivial guard: a single-user instance must not unlock pilot
    even with a textbook fresh-first-viewer match."""
    alice = await _make_viewer(db_session, "alice")
    await seed_achievements(db_session)

    now = datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc)
    created = now - timedelta(days=5)
    _index_row(db_session, item_id="movie-fresh", date_created=created)
    _make_session(
        db_session,
        emby_user_id="emby-alice",
        user_name=alice.username,
        item_id="movie-fresh",
        started_at=now,
        ended_at=now + timedelta(hours=1),
        suffix="alice",
    )
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert not await _ach_unlocked(db_session, alice.id, "secret_pilot")


# ── secret_late ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_late_unlocks_when_content_added_over_1_year_ago(db_session):
    alice = await _make_viewer(db_session, "alice")
    await seed_achievements(db_session)

    now = datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc)
    created = now - timedelta(days=400)
    _index_row(db_session, item_id="movie-old", date_created=created)
    _make_session(
        db_session,
        emby_user_id="emby-alice",
        user_name=alice.username,
        item_id="movie-old",
        started_at=now,
        ended_at=now + timedelta(hours=1),
        suffix="alice",
    )
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert await _ach_unlocked(db_session, alice.id, "secret_late")


@pytest.mark.asyncio
async def test_late_blocked_when_content_added_under_1_year(db_session):
    alice = await _make_viewer(db_session, "alice")
    await seed_achievements(db_session)

    now = datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc)
    created = now - timedelta(days=200)
    _index_row(db_session, item_id="movie-recent", date_created=created)
    _make_session(
        db_session,
        emby_user_id="emby-alice",
        user_name=alice.username,
        item_id="movie-recent",
        started_at=now,
        ended_at=now + timedelta(hours=1),
        suffix="alice",
    )
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert not await _ach_unlocked(db_session, alice.id, "secret_late")


@pytest.mark.asyncio
async def test_late_blocked_when_date_created_null(db_session):
    alice = await _make_viewer(db_session, "alice")
    await seed_achievements(db_session)

    now = datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc)
    _make_session(
        db_session,
        emby_user_id="emby-alice",
        user_name=alice.username,
        item_id="movie-no-meta",
        started_at=now,
        ended_at=now + timedelta(hours=1),
        suffix="alice",
    )
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert not await _ach_unlocked(db_session, alice.id, "secret_late")


@pytest.mark.asyncio
async def test_late_unlocks_at_exact_365_day_boundary(db_session):
    alice = await _make_viewer(db_session, "alice")
    await seed_achievements(db_session)

    now = datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc)
    created = now - timedelta(days=365)
    _index_row(db_session, item_id="movie-boundary", date_created=created)
    _make_session(
        db_session,
        emby_user_id="emby-alice",
        user_name=alice.username,
        item_id="movie-boundary",
        started_at=now,
        ended_at=now + timedelta(hours=1),
        suffix="alice",
    )
    await db_session.commit()

    await check_all_achievements(db_session, alice.id, alice.username)
    assert await _ach_unlocked(db_session, alice.id, "secret_late")


# ── Placeholder set hygiene ─────────────────────────────────────────────


def test_placeholder_set_no_longer_seals_emby_meta_family():
    for ach_id in ("secret_pilot", "secret_late"):
        assert ach_id not in PLACEHOLDER_IDS
