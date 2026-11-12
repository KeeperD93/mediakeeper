"""Plan of the watch XP recalculation: the rows the collector would pay today, against those held."""
import json
from datetime import timedelta

import pytest
from sqlalchemy import select, update

from constants.watch_xp_recalc import (
    LOST_NO_END,
    LOST_NO_STATS,
    SKIP_BEFORE_LEDGER,
    SKIP_COOLDOWN,
    SKIP_ERASED,
    SKIP_EXCLUDED,
    SKIP_NO_ACCOUNT,
    SKIP_NOT_EARNING,
    SKIP_PARALLEL,
)
from models.playback_stats import PlaybackCompletion
from models.portal.profile import UserProfile
from models.portal.xp_boost import XpBoostEvent
from models.portal.xp_ledger import XpLedger
from models.user import User
from services.portal.gdpr_erased import _identity_keys
from services.portal.xp import level_from_xp
from services.settings import set_setting
from services.stats_aggregator.users_admin import delete_user_stats, merge_user_stats
from services.stats_collector._measure import as_utc
from services.stats_collector.collect import pay_watch_xp
from tests._watch_xp_helpers import T, account, watched
from tests._watch_xp_recalc_helpers import (
    apply,
    give,
    plan,
    player,
    references,
    sitting,
)

pytestmark = pytest.mark.asyncio
HOUR = timedelta(hours=1)


async def _ledger_begins(db, user_id: int) -> None:
    """A first ledger row a day before ``T``: no title of the tests is too old."""
    await give(db, user_id, "daily_login", "2026-03-06", 2, T - 24 * HOUR)


async def test_the_plan_finds_exactly_what_the_collector_paid(db_session):
    db = db_session
    db.add(XpBoostEvent(name="Test Event", multiplier=1.5, starts_at=T + 2 * HOUR, ends_at=T + 4 * HOUR))
    await account(db, "alice")
    await account(db, "bob")
    ids = [
        await watched(db, "alice", at=T),
        await watched(db, "alice", item="EP-1", item_type="Episode", runtime=2700, at=T + 3 * HOUR),  # bonus
        await watched(db, "alice", at=T + 20 * HOUR),  # within 24 hours
        await watched(db, "alice", at=T + 30 * HOUR),
        await watched(db, "bob", item="EP-2", item_type="Episode", runtime=1320, at=T + HOUR),
        await watched(db, "bob", item="MOVIE-2", at=T + 5 * HOUR),
    ]
    await db.execute(update(PlaybackCompletion).where(PlaybackCompletion.id == ids[-1]).values(exclusive_seconds=0))
    await db.commit()
    await pay_watch_xp(db, ids)

    found = await plan(db)

    assert found.players and not any(p.changed for p in found.players)
    paid = (await db.execute(
        select(XpLedger.reference, XpLedger.xp, XpLedger.created_at).order_by(XpLedger.created_at, XpLedger.id)
    )).all()
    assert [(t.reference, t.xp, t.at) for t in found.targets] == [(ref, xp, as_utc(at)) for ref, xp, at in paid]
    assert found.skipped == {SKIP_COOLDOWN: 1, SKIP_PARALLEL: 1}


async def test_rows_no_watched_title_pays_any_more_are_taken_back(db_session):
    db = db_session
    alice, bob, carol, dave = [await account(db, name) for name in ("alice", "bob", "carol", "dave")]
    # Paid by the former rule for a film left paused, never watched to its end.
    await sitting(db, "alice", "MOVIE-9", T)
    await give(db, alice, "watch_movie", "MOVIE-9:2026-03-07", 10, T + 2 * HOUR)
    # Paid by the current rule, then Statistics > delete the user.
    await pay_watch_xp(db, [await watched(db, "bob", at=T + 3 * HOUR)])
    await delete_user_stats(db, "emby-bob")
    # Carol's statistics merged into Dave's: her title is now his.
    moved = await watched(db, "carol", item="MOVIE-3", at=T + 4 * HOUR)
    await pay_watch_xp(db, [moved])
    await merge_user_stats(db, "emby-carol", "emby-dave")

    found = await plan(db)

    for user_id in (alice, bob, carol):
        assert player(found, user_id).loses_all and player(found, user_id).xp_after == 0
    assert references(player(found, dave).inserted) == [f"MOVIE-3:c{moved}"]
    assert found.lost == {LOST_NO_END: 1, LOST_NO_STATS: 2}


async def test_a_title_reaching_an_account_by_its_name_is_paid_and_counted(db_session):
    erin = await account(db_session, "erin")
    # Another Emby user named like her account: the collector pays it to her.
    await watched(db_session, "erin", emby_id="emby-namesake", at=T)

    found = await plan(db_session)

    assert [t.user_id for t in found.targets] == [erin]
    assert found.namesakes == 1


async def test_titles_watched_before_the_ledger_began_are_left_out(db_session):
    alice = await account(db_session)
    await give(db_session, alice, "daily_login", "2026-03-07", 2, T)
    await watched(db_session, at=T - HOUR - timedelta(seconds=1))
    late = await watched(db_session, item="MOVIE-2", at=T - HOUR + timedelta(seconds=1))

    found = await plan(db_session)

    assert references(found.targets) == [f"MOVIE-2:c{late}"]
    assert found.skipped == {SKIP_BEFORE_LEDGER: 1}


async def test_a_title_watched_again_pays_once_per_24_hours(db_session):
    alice = await account(db_session)
    await _ledger_begins(db_session, alice)
    ids = [await watched(db_session, at=T + hours * HOUR) for hours in (0, 20, 30)]

    found = await plan(db_session)

    assert references(found.targets) == [f"MOVIE-1:c{ids[0]}", f"MOVIE-1:c{ids[2]}"]
    assert found.skipped == {SKIP_COOLDOWN: 1}


async def test_a_first_viewing_left_unpaid_takes_the_place_of_the_second(db_session):
    alice = await account(db_session)
    await _ledger_begins(db_session, alice)
    first = await watched(db_session, at=T)
    second = await watched(db_session, at=T + 20 * HOUR)
    await pay_watch_xp(db_session, [second])

    p = player(await plan(db_session), alice)

    assert references(p.inserted) == [f"MOVIE-1:c{first}"]
    assert references(p.deleted) == [f"MOVIE-1:c{second}"]


async def test_a_row_already_paid_keeps_its_bonus_when_the_event_is_switched_off(db_session):
    event = XpBoostEvent(name="Test Event", multiplier=2.0, starts_at=T - HOUR, ends_at=T + HOUR)
    db_session.add(event)
    alice = await account(db_session)
    await pay_watch_xp(db_session, [await watched(db_session)])
    event.enabled = False
    await db_session.commit()

    found = await plan(db_session)

    assert not player(found, alice).changed
    assert [row.xp for row in player(found, alice).kept] == [80]
    assert [t.xp for t in found.targets] == [40]


async def test_xp_earned_outside_the_ledger_stays(db_session):
    alice = await account(db_session)
    await db_session.execute(update(UserProfile).where(UserProfile.user_id == alice).values(xp=100))
    await give(db_session, alice, "watch_movie", "MOVIE-9:2026-03-07", 10, T - 2 * HOUR)
    await watched(db_session, at=T)

    p = player(await plan(db_session), alice)

    assert (p.xp, p.xp_after, p.level_after) == (110, 140, level_from_xp(140))


async def test_who_is_recalculated_and_why_a_title_is_left_out(db_session):
    db = db_session
    frank, grace = await account(db, "frank"), await account(db, "grace")
    await _ledger_begins(db, frank)
    await db.execute(update(User).where(User.id == frank).values(is_active=False))  # deactivated: recalculated
    await db.execute(update(UserProfile).where(UserProfile.user_id == grace).values(source="local"))
    await set_setting(db, "stats.exclusions", json.dumps([{"mode": "contains", "value": "trailer"}]))
    await set_setting(db, next(iter(_identity_keys("emby-ivan", None))), "1")
    paid = await watched(db, "frank", at=T)
    await watched(db, "grace", at=T)
    await watched(db, "henry", at=T)  # no account
    await watched(db, "frank", item="MOVIE-2", item_name="Test Trailer", at=T)
    await watched(db, "ivan", at=T)  # erased at their request

    found = await plan(db)

    assert references(found.targets) == [f"MOVIE-1:c{paid}"]
    assert found.skipped == {SKIP_NOT_EARNING: 1, SKIP_NO_ACCOUNT: 1, SKIP_EXCLUDED: 1, SKIP_ERASED: 1}


async def test_a_plan_applied_leaves_nothing_to_plan(db_session):
    db = db_session
    alice, _bob, carol, _erin = [await account(db, name) for name in ("alice", "bob", "carol", "erin")]
    await db.execute(update(UserProfile).where(UserProfile.user_id == alice).values(xp=100))
    await sitting(db, "alice", "MOVIE-9", T)
    await give(db, alice, "watch_movie", "MOVIE-9:2026-03-07", 10, T - 2 * HOUR)
    await give(db, carol, "watch_movie", "MOVIE-8:2026-03-07", 10, T - 2 * HOUR)
    await watched(db, "alice", at=T - 3 * HOUR - timedelta(seconds=1))  # before the ledger
    # Due just after the start: once written, its row must not move the start earlier.
    first = await watched(db, "alice", at=T - 2.5 * HOUR)
    await pay_watch_xp(db, [await watched(db, "alice", at=T + 20 * HOUR)])
    await watched(db, "alice", at=T + 30 * HOUR)
    await pay_watch_xp(db, [await watched(db, "bob", item="EP-1", item_type="Episode", runtime=2700, at=T)])
    await delete_user_stats(db, "emby-bob")
    await watched(db, "erin", emby_id="emby-namesake", at=T + HOUR)
    found = await plan(db)
    assert sum(p.changed for p in found.players) == 4 and f"MOVIE-1:c{first}" in references(found.targets)

    await apply(db, found)
    again = await plan(db)

    assert not any(p.changed for p in again.players)
    assert again.targets == found.targets
