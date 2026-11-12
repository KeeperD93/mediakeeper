"""Watch XP rule: 20 XP per hour of a title watched alone, paid and dated when it counts as watched."""
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.playback_stats import PlaybackCompletion
from models.portal.profile import UserProfile
from models.portal.xp_boost import XpBoostEvent
from models.portal.xp_ledger import XpLedger
from services.instance_time import INSTANCE_TIMEZONE_KEY
from services.portal.monthly_ranking import month_rankings
from services.portal.user_import import ensure_user_for_emby_session
from services.portal.xp import WatchedTitle, grant_completion_xp, watch_xp_eligible
from services.portal.xp._watch import watch_xp_amount
from services.settings import set_setting
from services.stats_collector._measure import as_utc
from services.stats_collector.collect import pay_watch_xp
from tests._watch_xp_helpers import T, account, watch_rows, watched


@pytest.mark.parametrize(("runtime", "xp"), [
    (7200, 40), (2700, 15), (1320, 7), (450, 3), (60, 1), (1, 1),
])
def test_20_xp_per_hour_rounded_to_the_nearest_and_at_least_1(runtime, xp):
    assert watch_xp_amount(runtime) == xp


@pytest.mark.parametrize(("item_type", "runtime", "alone", "earns"), [
    ("Movie", 7200, 5400, True),
    ("Movie", 7200, 5399, False),  # another title played at the same time
    ("Episode", 2700, 2700, True),
    ("Audio", 300, 300, False),
    ("Movie", 0, 0, False),
])
def test_only_a_movie_or_an_episode_watched_alone_long_enough_earns(item_type, runtime, alone, earns):
    title = WatchedTitle(1, "MOVIE-1", item_type, runtime, alone, T)
    assert watch_xp_eligible(title) is earns


@pytest.mark.asyncio
async def test_a_watched_title_pays_its_runtime_dated_when_it_counted(db_session):
    await account(db_session)
    film = await watched(db_session)
    episode = await watched(db_session, item="EP-1", item_type="Episode", runtime=2700, at=T + timedelta(hours=3))

    assert await pay_watch_xp(db_session, [film, episode]) == 2

    assert await watch_rows(db_session) == [
        ("watch_movie", f"MOVIE-1:c{film}", 40), ("watch_episode", f"EP-1:c{episode}", 15),
    ]
    dates = (await db_session.execute(select(XpLedger.created_at).order_by(XpLedger.id))).scalars().all()
    assert [as_utc(at) for at in dates] == [T, T + timedelta(hours=3)]


@pytest.mark.asyncio
async def test_a_title_watched_late_on_the_31st_counts_in_the_month_of_the_instance_clock(db_session):
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")
    alice = await account(db_session)
    late = datetime(2026, 1, 31, 23, 30, tzinfo=UTC)  # 00:30 on 1 February in Paris
    await pay_watch_xp(db_session, [await watched(db_session, at=late)])

    months = await month_rankings(db_session, ZoneInfo("Europe/Paris"), datetime(2026, 3, 1, tzinfo=UTC))

    assert {month: [(e.user_id, e.xp) for e in entries] for month, entries in months.items()} == {
        (2026, 2): [(alice, 40)],
    }


@pytest.mark.asyncio
async def test_a_title_watched_again_within_24_hours_pays_once(db_session):
    await account(db_session)
    ids = [await watched(db_session, at=T + timedelta(hours=hours)) for hours in (0, 20, 30)]

    await pay_watch_xp(db_session, ids)

    # +20 h falls within 24 hours of the paid one; +30 h no longer does.
    assert [reference for _, reference, _ in await watch_rows(db_session)] == [
        f"MOVIE-1:c{ids[0]}", f"MOVIE-1:c{ids[2]}",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("exclusion", [
    {"mode": "exact", "value": "Theme Song"},
    {"mode": "contains", "value": "theme"},
])
async def test_an_excluded_title_earns_nothing(db_session, exclusion):
    await set_setting(db_session, "stats.exclusions", json.dumps([exclusion]))
    await account(db_session)

    assert await pay_watch_xp(db_session, [await watched(db_session, item_name="Theme Song")]) == 0

    assert await watch_rows(db_session) == []


@pytest.mark.asyncio
async def test_the_bonus_is_the_one_active_when_the_title_counted(db_session):
    now = datetime.now(UTC)
    db_session.add_all([
        XpBoostEvent(name="Then", multiplier=2.0, starts_at=T - timedelta(hours=1), ends_at=T + timedelta(hours=1)),
        XpBoostEvent(
            name="Then, switched off", multiplier=5.0, enabled=False,
            starts_at=T - timedelta(hours=1), ends_at=T + timedelta(hours=1),
        ),
        XpBoostEvent(name="Now", multiplier=3.0, starts_at=now - timedelta(hours=1), ends_at=now + timedelta(hours=1)),
    ])
    await account(db_session)

    await pay_watch_xp(db_session, [await watched(db_session)])

    assert [xp for _, _, xp in await watch_rows(db_session)] == [80]


@pytest.mark.asyncio
@pytest.mark.parametrize(("runtime", "multiplier", "xp"), [(2700, 1.5, 23), (60, 0.4, 1)])
async def test_a_bonus_rounds_to_the_nearest_and_a_title_still_pays_at_least_1_xp(db_session, runtime, multiplier, xp):
    db_session.add(XpBoostEvent(
        name="Test Event", multiplier=multiplier, starts_at=T - timedelta(hours=1), ends_at=T + timedelta(hours=1),
    ))
    await account(db_session)

    await pay_watch_xp(db_session, [await watched(db_session, runtime=runtime)])

    assert [paid for _, _, paid in await watch_rows(db_session)] == [xp]


@pytest.mark.asyncio
async def test_a_refused_payment_ends_its_transaction_and_keeps_the_pending_work(db_session):
    alice = await account(db_session)
    done = await db_session.get(PlaybackCompletion, await watched(db_session))
    title = WatchedTitle.of(done)
    assert await grant_completion_xp(db_session, alice, title)

    profile = (await db_session.execute(select(UserProfile).where(UserProfile.user_id == alice))).scalar_one()
    profile.bio = "Test bio"
    assert await grant_completion_xp(db_session, alice, title) is None  # within 24 hours of itself

    assert not db_session.in_transaction()
    async with AsyncSession(db_session.bind) as reader:
        assert await reader.scalar(select(UserProfile.bio).where(UserProfile.user_id == alice)) == "Test bio"


@pytest.mark.asyncio
async def test_a_failed_payment_costs_only_its_own_title(db_session):
    await account(db_session, "alice")
    bob = await account(db_session, "bob")
    ids = [await watched(db_session, "alice"), await watched(db_session, "bob")]

    async def _fails_for_alice(db, *, emby_username, emby_user_id):
        if emby_username == "alice":  # a write the database refuses breaks the shared session
            db.add(XpLedger(user_id=0, action=None, reference="broken"))
            await db.flush()
        return await ensure_user_for_emby_session(db, emby_username=emby_username, emby_user_id=emby_user_id)

    with patch("services.stats_collector._watch_xp.ensure_user_for_emby_session", new=_fails_for_alice):
        assert await pay_watch_xp(db_session, ids) == 1

    paid = (await db_session.execute(select(XpLedger.user_id))).scalars().all()
    assert paid == [bob]
