"""Regular and Faithful: tiers earned on the longest run, bars on the run in progress."""
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from core.security import hash_password
from models.playback_stats import PlaybackSession
from models.portal.achievement import UserAchievement
from models.portal.profile import UserProfile
from models.user import User
from services.instance_time import INSTANCE_TIMEZONE_KEY
from services.portal import achievements_checks_local_time
from services.portal.achievements import check_all_achievements, seed_achievements
from services.settings import set_setting


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
    db.add(UserProfile(user_id=user.id, display_name=username, role="viewer", account_active=True))
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


def _freeze(monkeypatch, module, moment: datetime) -> None:
    class Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            return moment

    monkeypatch.setattr(module, "datetime", Frozen)


@pytest.mark.asyncio
async def test_a_past_run_earns_its_tier_and_the_bar_shows_the_run_in_progress(
    db_session, monkeypatch,
):
    alice = await _viewer(db_session)
    await seed_achievements(db_session)
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")
    now = _at(2026, 10, 16, 18)
    for day in range(3):
        _session(db_session, now - timedelta(days=30 + day))
    _session(db_session, now)
    _session(db_session, now - timedelta(days=1))
    await db_session.commit()
    _freeze(monkeypatch, achievements_checks_local_time, now)

    await check_all_achievements(db_session, alice.id, alice.username)

    assert await _unlocked(db_session, alice, "regular_1")
    next_tier = await _progress(db_session, alice, "regular_2")
    assert (next_tier.unlocked, next_tier.progress) == (False, 2)
    faithful = await _progress(db_session, alice, "secret_dedication")
    assert (faithful.unlocked, faithful.progress) == (False, 2)


async def _with_a_past_run(db, monkeypatch) -> User:
    alice = await _viewer(db)
    await seed_achievements(db)
    now = _at(2026, 10, 16, 18)
    for day in range(3):
        _session(db, now - timedelta(days=30 + day))
    await db.commit()
    _freeze(monkeypatch, achievements_checks_local_time, now)
    return alice


@pytest.mark.asyncio
async def test_a_past_run_earns_nothing_until_a_zone_is_chosen(db_session, monkeypatch):
    alice = await _with_a_past_run(db_session, monkeypatch)

    await check_all_achievements(db_session, alice.id, alice.username)
    tier = await _progress(db_session, alice, "regular_1")
    assert (tier.unlocked, tier.progress) == (False, 0)

    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")
    await check_all_achievements(db_session, alice.id, alice.username)
    assert await _unlocked(db_session, alice, "regular_1")


@pytest.mark.asyncio
async def test_utc_chosen_on_purpose_is_a_chosen_zone(db_session, monkeypatch):
    alice = await _with_a_past_run(db_session, monkeypatch)
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "UTC")

    await check_all_achievements(db_session, alice.id, alice.username)
    assert await _unlocked(db_session, alice, "regular_1")


@pytest.mark.asyncio
async def test_a_zone_that_cannot_be_loaded_is_not_a_chosen_zone(db_session, monkeypatch):
    alice = await _with_a_past_run(db_session, monkeypatch)
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Mars/Olympus")

    await check_all_achievements(db_session, alice.id, alice.username)
    assert not await _unlocked(db_session, alice, "regular_1")


@pytest.mark.asyncio
async def test_a_play_dated_tomorrow_earns_no_tier(db_session, monkeypatch):
    alice = await _viewer(db_session)
    await seed_achievements(db_session)
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")
    now = _at(2026, 10, 16, 12)
    for day in range(-1, 2):
        _session(db_session, now - timedelta(days=day))
    await db_session.commit()
    _freeze(monkeypatch, achievements_checks_local_time, now)

    await check_all_achievements(db_session, alice.id, alice.username)

    tier = await _progress(db_session, alice, "regular_1")
    assert (tier.unlocked, tier.progress) == (False, 2)


@pytest.mark.asyncio
async def test_the_day_streak_tier_follows_the_saved_zone(db_session, monkeypatch):
    """22:22 UTC is 00:22 the next day in Paris: three days in a row there, not in UTC."""
    alice = await _viewer(db_session)
    await seed_achievements(db_session)
    _session(db_session, _at(2026, 10, 14, 22, 22))
    _session(db_session, _at(2026, 10, 16, 16, 49))
    _session(db_session, _at(2026, 10, 17, 16, 49))
    await db_session.commit()
    _freeze(monkeypatch, achievements_checks_local_time, _at(2026, 10, 17, 18))

    await check_all_achievements(db_session, alice.id, alice.username)
    assert not await _unlocked(db_session, alice, "regular_1")

    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")
    await check_all_achievements(db_session, alice.id, alice.username)
    assert await _unlocked(db_session, alice, "regular_1")


@pytest.mark.asyncio
async def test_today_of_the_day_streak_follows_the_saved_zone(db_session, monkeypatch):
    """At 18:00 UTC on the 16th it is the 17th in Auckland: a run ending on the 15th is over."""
    alice = await _viewer(db_session)
    await seed_achievements(db_session)
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Pacific/Auckland")
    _session(db_session, _at(2026, 10, 14, 0, 30))
    _session(db_session, _at(2026, 10, 15, 0, 30))
    await db_session.commit()
    _freeze(monkeypatch, achievements_checks_local_time, _at(2026, 10, 16, 18))

    await check_all_achievements(db_session, alice.id, alice.username)

    assert (await _progress(db_session, alice, "regular_1")).progress == 0
