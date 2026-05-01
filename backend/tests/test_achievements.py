"""Tests for the Demandes achievements service."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from core.security import hash_password
from models.portal.achievement import Achievement
from models.portal.achievement import UserAchievement
from models.portal.profile import UserProfile
from models.playback_stats import LibraryCache, PlaybackSession
from models.user import User
from services.portal.achievements import check_all_achievements, seed_achievements


def _make_session(
    session_key: str,
    item_id: str,
    item_name: str,
    item_type: str,
    started_at: datetime,
    *,
    library_name: str,
    series_name: str | None = None,
    season_number: int | None = None,
    episode_number: int | None = None,
) -> PlaybackSession:
    return PlaybackSession(
        session_key=session_key,
        user_id="emby-viewer",
        user_name="viewer",
        item_id=item_id,
        item_name=item_name,
        item_type=item_type,
        series_name=series_name,
        season_number=season_number,
        episode_number=episode_number,
        library_name=library_name,
        started_at=started_at,
        last_seen_at=started_at + timedelta(minutes=45),
        ended_at=started_at + timedelta(minutes=45),
        is_active=False,
    )


@pytest.mark.asyncio
async def test_check_all_achievements_unlocks_special_badges_and_stacks_xp(db_session):
    user = User(
        username="viewer",
        hashed_password=hash_password("ViewerPassword123!"),
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    profile = UserProfile(
        user_id=user.id,
        display_name="Viewer Nick",
        role="viewer",
        account_active=True,
    )
    db_session.add(profile)
    db_session.add_all([
        LibraryCache(lib_id="movies", name="Movies"),
        LibraryCache(lib_id="series", name="Series"),
    ])
    await db_session.commit()
    await db_session.refresh(profile)

    await seed_achievements(db_session)

    saturday = datetime(2026, 4, 11, 10, 0, tzinfo=timezone.utc)
    sunday = datetime(2026, 4, 12, 10, 0, tzinfo=timezone.utc)

    sessions = [
        _make_session(
            f"movie-{idx}",
            f"movie-{idx}",
            f"Movie {idx}",
            "Movie",
            saturday + timedelta(minutes=idx * 30) if idx < 7 else sunday + timedelta(minutes=(idx - 7) * 30),
            library_name="Movies",
        )
        for idx in range(10)
    ]
    sessions.extend([
        _make_session(
            "ep-1",
            "ep-1",
            "Episode 1",
            "Episode",
            saturday + timedelta(hours=5),
            library_name="Series",
            series_name="Binge Show",
            season_number=1,
            episode_number=1,
        ),
        _make_session(
            "ep-2",
            "ep-2",
            "Episode 2",
            "Episode",
            saturday + timedelta(hours=6),
            library_name="Series",
            series_name="Binge Show",
            season_number=1,
            episode_number=2,
        ),
        _make_session(
            "ep-3",
            "ep-3",
            "Episode 3",
            "Episode",
            saturday + timedelta(hours=7),
            library_name="Series",
            series_name="Binge Show",
            season_number=1,
            episode_number=3,
        ),
    ])
    db_session.add_all(sessions)
    await db_session.commit()

    unlocked = await check_all_achievements(db_session, user.id)
    await db_session.refresh(profile)

    unlocked_ids = {item["achievement_id"] for item in unlocked}
    assert {
        "movie_buff_1",
        "weekend_warrior_1",
        "season_binge_1",
        "explorer_1",
    }.issubset(unlocked_ids)
    total_unlocked_xp = await db_session.scalar(
        select(func.coalesce(func.sum(Achievement.xp_reward), 0))
        .join(UserAchievement, UserAchievement.achievement_id == Achievement.id)
        .where(
            UserAchievement.user_id == user.id,
            UserAchievement.unlocked == True,  # noqa: E712
        )
    )
    assert profile.xp == total_unlocked_xp


@pytest.mark.asyncio
async def test_seed_achievements_ignores_non_model_metadata_keys(db_session):
    await seed_achievements(db_session)

    meta = await db_session.get(Achievement, "meta_master_watching")

    assert meta is not None
    assert meta.category == "mastery"
    assert not hasattr(meta, "requires")


def test_user_achievement_model_declares_unique_user_badge_index():
    unique_indexes = {
        index.name: [column.name for column in index.columns]
        for index in UserAchievement.__table__.indexes
        if index.unique
    }

    assert unique_indexes["uq_user_achievements_user_achievement"] == [
        "user_id",
        "achievement_id",
    ]
