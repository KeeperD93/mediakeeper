"""The saved time zone reaches the trophies, through the real check pass."""
import json
import logging
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, select

from core.security import hash_password
from models.playback_stats import PlaybackSession
from models.portal.achievement import Achievement, UserAchievement
from models.portal.profile import UserProfile
from models.user import User
from services.instance_time import INSTANCE_TIMEZONE_KEY
from services.portal import achievements_checks_local_time
from services.portal.achievement_defs import ACHIEVEMENT_DEFS
from services.portal.achievements import check_all_achievements, seed_achievements
from services.portal.achievements_checks_local_time import LOCAL_TIME_CONDITIONS
from services.portal.achievements_validation import KNOWN_CONDITION_TYPES
from services.settings import set_setting
from services.stats_collector._measure import spread_over_hours


def _at(*parts: int) -> datetime:
    return datetime(*parts, tzinfo=UTC)


async def _viewer(db, username: str = "alice") -> User:
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
        user_id=user.id, display_name=username, role="viewer", account_active=True,
        emby_user_id=f"emby-{username}",
    ))
    await db.commit()
    return user


def _session(db, started: datetime, *, user: str = "alice", item: str = "item-1", **fields) -> None:
    seconds = fields.pop("seconds", 60)
    db.add(PlaybackSession(
        session_key=f"{user}-{item}-{started.timestamp()}",
        user_id=f"emby-{user}",
        user_name=user,
        item_id=item,
        item_name=fields.pop("item_name", "Test Movie"),
        item_type=fields.pop("item_type", "Movie"),
        started_at=started,
        last_seen_at=started,
        ended_at=fields.pop("ended_at", started + timedelta(seconds=seconds)),
        measured=True,
        exclusive_seconds=seconds,
        watched_by_hour=spread_over_hours(started, seconds),
        **fields,
    ))


async def _progress(db, user: User, achievement_id: str) -> UserAchievement | None:
    return (await db.execute(
        select(UserAchievement).where(
            UserAchievement.user_id == user.id,
            UserAchievement.achievement_id == achievement_id,
        )
    )).scalar_one_or_none()


async def _unlocked(db, user: User, achievement_id: str) -> bool:
    row = await _progress(db, user, achievement_id)
    return bool(row and row.unlocked)


def _first_tier(condition: str) -> str:
    return next(
        d["id"] for d in ACHIEVEMENT_DEFS
        if d["condition_type"] == condition and d["threshold"] == 1
    )


def test_every_local_rule_has_a_place_in_the_catalogue():
    assert set(LOCAL_TIME_CONDITIONS) <= KNOWN_CONDITION_TYPES
    declared = {d["condition_type"] for d in ACHIEVEMENT_DEFS}
    assert set(LOCAL_TIME_CONDITIONS) <= declared


@pytest.mark.asyncio
async def test_a_local_rule_alone_in_the_catalogue_still_gets_its_rows(db_session):
    alice = await _viewer(db_session)
    await seed_achievements(db_session)
    await db_session.execute(delete(Achievement).where(Achievement.id != "secret_triple"))
    for item in ("item-1", "item-2", "item-3"):
        _session(db_session, _at(2026, 1, 15, 12), item=item)
    await db_session.commit()

    await check_all_achievements(db_session, alice.id)
    assert await _unlocked(db_session, alice, "secret_triple")


@pytest.mark.asyncio
async def test_excluded_titles_count_for_no_local_rule(db_session):
    """The list of titles left out of the statistics holds here too, day streak included."""
    alice = await _viewer(db_session)
    await seed_achievements(db_session)
    exclusions = [{"mode": "exact", "value": "Test Intro"}]
    await set_setting(db_session, "stats.exclusions", json.dumps(exclusions))
    _session(db_session, _at(2026, 1, 15, 2), item_name="Test Intro")
    await db_session.commit()

    await check_all_achievements(db_session, alice.id)
    assert not await _unlocked(db_session, alice, _first_tier("night_watch"))


@pytest.mark.asyncio
async def test_a_date_at_the_edge_of_the_calendar_loses_no_pass(db_session, caplog):
    alice = await _viewer(db_session)
    await seed_achievements(db_session)
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "America/New_York")
    _session(db_session, datetime(1, 1, 1, tzinfo=UTC))
    _session(db_session, _at(2026, 1, 16, 6))  # 01:00 in New York
    await db_session.commit()

    with caplog.at_level(logging.ERROR, logger="mediakeeper.portal.achievements"):
        await check_all_achievements(db_session, alice.id)

    assert "check pass failed" not in caplog.text
    assert await _unlocked(db_session, alice, _first_tier("night_watch"))


@pytest.mark.asyncio
async def test_a_pass_that_fails_still_reports_what_it_unlocked(db_session, monkeypatch, caplog):
    """The lonely new year read fails once the triple is granted: the triple is still returned."""
    alice = await _viewer(db_session)
    await seed_achievements(db_session)
    for item in ("item-1", "item-2", "item-3"):
        _session(db_session, _at(2026, 1, 15, 12), item=item)
    await db_session.commit()

    async def read_fails(*_args):
        raise RuntimeError("Test read failure")

    monkeypatch.setattr(achievements_checks_local_time, "_is_lonely", read_fails)
    with caplog.at_level(logging.ERROR, logger="mediakeeper.portal.achievements"):
        unlocks = await check_all_achievements(db_session, alice.id)

    assert "secret_triple" in {u["achievement_id"] for u in unlocks}
    assert await _unlocked(db_session, alice, "secret_triple")
    failed = [
        getattr(r, "pass", None) for r in caplog.records
        if r.getMessage() == "achievements check pass failed"
    ]
    assert failed == ["local_time"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("condition", "moment"),
    [
        ("night_watch", _at(2026, 1, 15, 23, 30)),
        ("secret_early_bird", _at(2026, 1, 16, 4, 30)),
        ("secret_newyear", _at(2025, 12, 31, 23, 30)),
        ("secret_ghost", _at(2026, 1, 16, 0, 30)),
        ("secret_countdown", _at(2026, 1, 15, 23, 0)),
    ],
)
async def test_a_trophy_follows_the_saved_zone(db_session, condition, moment):
    alice = await _viewer(db_session)
    await seed_achievements(db_session)
    _session(db_session, moment)
    await db_session.commit()
    achievement = _first_tier(condition)

    await check_all_achievements(db_session, alice.id)
    assert not await _unlocked(db_session, alice, achievement)

    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")
    await check_all_achievements(db_session, alice.id)
    assert await _unlocked(db_session, alice, achievement)


@pytest.mark.asyncio
async def test_lonely_new_year_follows_the_local_calendar(db_session):
    """The 30th at 23:30 UTC is the 31st in Paris; a second player makes the rule possible."""
    alice = await _viewer(db_session)
    await _viewer(db_session, "bob")
    await seed_achievements(db_session)
    _session(db_session, _at(2026, 12, 30, 23, 30))
    _session(db_session, _at(2026, 6, 1, 12), user="bob")
    await db_session.commit()

    await check_all_achievements(db_session, alice.id)
    assert not await _unlocked(db_session, alice, "secret_lonely")

    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")
    await check_all_achievements(db_session, alice.id)
    assert await _unlocked(db_session, alice, "secret_lonely")


@pytest.mark.asyncio
async def test_lonely_needs_nobody_else_watching_and_a_second_player(db_session):
    alice = await _viewer(db_session)
    await seed_achievements(db_session)
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")
    moment = _at(2026, 12, 31, 12)
    _session(db_session, moment)
    await db_session.commit()

    await check_all_achievements(db_session, alice.id)
    assert not await _unlocked(db_session, alice, "secret_lonely")

    await _viewer(db_session, "bob")
    _session(db_session, moment, user="bob")
    await db_session.commit()
    await check_all_achievements(db_session, alice.id)
    assert not await _unlocked(db_session, alice, "secret_lonely")

    # One new year session alone is enough, even with company on another.
    _session(db_session, _at(2026, 12, 31, 18))
    await db_session.commit()
    await check_all_achievements(db_session, alice.id)
    assert await _unlocked(db_session, alice, "secret_lonely")


@pytest.mark.asyncio
async def test_the_all_nighter_trophy_receives_the_saved_zone(db_session):
    """Seven real hours make a night only on the clock of Paris, when the clocks go forward."""
    alice = await _viewer(db_session)
    await seed_achievements(db_session)
    start = _at(2026, 3, 28, 21)
    _session(db_session, start, ended_at=start + timedelta(hours=7))
    await db_session.commit()

    await check_all_achievements(db_session, alice.id)
    assert not await _unlocked(db_session, alice, "secret_allnight")

    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")
    await check_all_achievements(db_session, alice.id)
    assert await _unlocked(db_session, alice, "secret_allnight")


@pytest.mark.asyncio
async def test_the_king_trophy_receives_the_saved_zone(db_session):
    """Bob's long session of December 31 at 23:30 UTC falls in January in Paris."""
    alice = await _viewer(db_session)
    await _viewer(db_session, "bob")
    await seed_achievements(db_session)
    for month in range(1, 13):
        moment = _at(2025, month, 15, 12)
        _session(db_session, moment, ended_at=moment + timedelta(hours=2))
        _session(db_session, moment, user="bob", ended_at=moment + timedelta(hours=1))
    moment = _at(2025, 12, 31, 23, 30)
    _session(db_session, moment, user="bob", ended_at=moment + timedelta(hours=10))
    await db_session.commit()

    await check_all_achievements(db_session, alice.id)
    assert not await _unlocked(db_session, alice, "secret_king")

    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")
    await check_all_achievements(db_session, alice.id)
    assert await _unlocked(db_session, alice, "secret_king")
