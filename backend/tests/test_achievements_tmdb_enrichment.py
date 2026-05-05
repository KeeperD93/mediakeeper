"""TMDB-enrichment achievements: Time Traveler, The Classic, The Purist.

Five trophies graduated from the placeholder set in this batch — they
all consume the two new columns on ``emby_tmdb_index``
(``production_year`` and ``original_language``).

Tests cover:
* the three ``time_traveler_*`` tiers (3 / 5 / 7 distinct decades),
* the NULL-year guard so unsynced media never inflates the count,
* the lifetime ``secret_classic`` (any pre-1970 session),
* the threshold-50 ``secret_purist`` and its language-mismatch guard,
* the ISO 639-1↔639-2 helper, suffix and case insensitivity included,
* the placeholder set no longer sealing this family.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from core.security import hash_password
from models.portal.achievement import UserAchievement
from models.portal.emby_tmdb_index import EmbyTmdbIndex
from models.portal.profile import UserProfile
from models.playback_stats import PlaybackSession
from models.user import User
from services.portal.achievement_defs_constants import PLACEHOLDER_IDS
from services.portal.achievements import (
    check_all_achievements,
    seed_achievements,
)
from services.portal.iso_lang_map import audio_matches_original
from sqlalchemy import select


# ── Helpers ─────────────────────────────────────────────────────────────


async def _make_viewer(db, username: str = "tmdb-viewer") -> User:
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


def _seed_session_with_index(
    db,
    *,
    username: str,
    item_id: str,
    started: datetime,
    production_year: int | None = None,
    audio_language: str | None = None,
    original_language: str | None = None,
    item_type: str = "Movie",
) -> None:
    """Insert a PlaybackSession + a matching emby_tmdb_index row.

    The two are linked through ``item_id`` ↔ ``emby_item_id`` — the
    same join the production checks rely on.
    """
    db.add(PlaybackSession(
        session_key=f"sess-{item_id}",
        user_id="emby-viewer",
        user_name=username,
        item_id=item_id,
        item_name=f"Item {item_id}",
        item_type=item_type,
        library_name="Movies",
        started_at=started,
        last_seen_at=started + timedelta(minutes=120),
        ended_at=started + timedelta(minutes=120),
        is_active=False,
        audio_language=audio_language,
    ))
    if production_year is not None or original_language is not None:
        db.add(EmbyTmdbIndex(
            emby_item_id=item_id,
            tmdb_id=hash(item_id) % 1_000_000,
            media_type="movie",
            title=f"Item {item_id}",
            production_year=production_year,
            original_language=original_language,
        ))


async def _ach_unlocked(db, user_id: int, ach_id: str) -> bool:
    row = (await db.execute(
        select(UserAchievement).where(
            UserAchievement.user_id == user_id,
            UserAchievement.achievement_id == ach_id,
        )
    )).scalar_one_or_none()
    return bool(row and row.unlocked)


# ── 1. time_traveler_* unlocks at 3 / 5 / 7 distinct decades ────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("decades_count,expected", [
    (3, "time_traveler_1"),
    (5, "time_traveler_2"),
    (7, "time_traveler_3"),
])
async def test_decades_watched_unlocks_at_thresholds(db_session, decades_count, expected):
    user = await _make_viewer(db_session)
    await seed_achievements(db_session)

    started_base = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    # Pick distinct decades 1950, 1960, …, 1950+10*(n-1)
    for i in range(decades_count):
        _seed_session_with_index(
            db_session,
            username=user.username,
            item_id=f"movie-decade-{i}",
            started=started_base + timedelta(hours=i),
            production_year=1950 + 10 * i + 5,  # mid-decade
        )
    await db_session.commit()

    unlocks = await check_all_achievements(db_session, user.id, user.username)
    unlocked_ids = {row["achievement_id"] for row in unlocks}
    assert expected in unlocked_ids


# ── 2. Sessions without an indexed year never count toward the trophy ───


@pytest.mark.asyncio
async def test_decades_watched_skips_null_production_year(db_session):
    user = await _make_viewer(db_session)
    await seed_achievements(db_session)

    started_base = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    # 3 sessions on 3 different decades, but each row's index entry
    # has production_year = NULL (e.g. unsynced media).
    for i in range(3):
        _seed_session_with_index(
            db_session,
            username=user.username,
            item_id=f"movie-null-{i}",
            started=started_base + timedelta(hours=i),
            production_year=None,
            original_language=None,
        )
    # An additional session whose item_id has no index row at all.
    db_session.add(PlaybackSession(
        session_key="sess-orphan",
        user_id="emby-viewer",
        user_name=user.username,
        item_id="movie-orphan",
        item_name="Orphan",
        item_type="Movie",
        library_name="Movies",
        started_at=started_base + timedelta(hours=10),
        last_seen_at=started_base + timedelta(hours=12),
        ended_at=started_base + timedelta(hours=12),
        is_active=False,
    ))
    await db_session.commit()

    await check_all_achievements(db_session, user.id, user.username)
    assert not await _ach_unlocked(db_session, user.id, "time_traveler_1")


# ── 3. secret_classic — pre-1970 only ───────────────────────────────────


@pytest.mark.asyncio
async def test_secret_classic_unlocks_when_year_lt_1970(db_session):
    user = await _make_viewer(db_session)
    await seed_achievements(db_session)

    _seed_session_with_index(
        db_session,
        username=user.username,
        item_id="movie-1965",
        started=datetime(2026, 1, 1, 14, 0, tzinfo=timezone.utc),
        production_year=1965,
    )
    await db_session.commit()

    await check_all_achievements(db_session, user.id, user.username)
    assert await _ach_unlocked(db_session, user.id, "secret_classic")


@pytest.mark.asyncio
async def test_secret_classic_does_not_unlock_for_post_1970(db_session):
    user = await _make_viewer(db_session)
    await seed_achievements(db_session)

    _seed_session_with_index(
        db_session,
        username=user.username,
        item_id="movie-1971",
        started=datetime(2026, 1, 1, 14, 0, tzinfo=timezone.utc),
        production_year=1971,
    )
    await db_session.commit()

    await check_all_achievements(db_session, user.id, user.username)
    assert not await _ach_unlocked(db_session, user.id, "secret_classic")


# ── 4. secret_purist — 50 OV sessions, mismatches don't count ───────────


@pytest.mark.asyncio
async def test_secret_purist_unlocks_at_threshold_50(db_session):
    user = await _make_viewer(db_session)
    await seed_achievements(db_session)

    started_base = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    # 50 OV sessions: French audio on French original-language titles.
    for i in range(50):
        _seed_session_with_index(
            db_session,
            username=user.username,
            item_id=f"movie-vo-{i}",
            started=started_base + timedelta(hours=i),
            production_year=2010,  # any year, irrelevant here
            audio_language="fre",
            original_language="fr",
        )
    # A handful of dubbed sessions (English audio on French original)
    # that must NOT count toward the threshold.
    for i in range(10):
        _seed_session_with_index(
            db_session,
            username=user.username,
            item_id=f"movie-dub-{i}",
            started=started_base + timedelta(hours=100 + i),
            production_year=2010,
            audio_language="eng",
            original_language="fr",
        )
    await db_session.commit()

    await check_all_achievements(db_session, user.id, user.username)
    assert await _ach_unlocked(db_session, user.id, "secret_purist")


# ── 5. iso_lang_map helper ──────────────────────────────────────────────


@pytest.mark.parametrize("audio,original,expected", [
    ("fre", "fr", True),
    ("FRE", "fr", True),
    ("fre-FR", "fr", True),
    ("fre-fr", "FR", True),
    ("eng", "fr", False),
    ("jpn", "ja", True),
    ("chi-CN", "zh", True),
    (None, "fr", False),
    ("fre", None, False),
    ("", "fr", False),
    ("xx", "fr", False),  # unknown audio code, but won't equal "fre"
    ("fre", "xx", False),  # unknown original, mapping returns None
])
def test_audio_matches_original_handles_iso_mismatch_and_suffix(audio, original, expected):
    assert audio_matches_original(audio, original) is expected


# ── 6. Placeholder set no longer seals the TMDB family ──────────────────


def test_placeholder_set_no_longer_seals_tmdb_family():
    for ach_id in (
        "time_traveler_1",
        "time_traveler_2",
        "time_traveler_3",
        "secret_classic",
        "secret_purist",
    ):
        assert ach_id not in PLACEHOLDER_IDS
