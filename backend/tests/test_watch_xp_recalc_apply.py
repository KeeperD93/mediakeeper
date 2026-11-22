"""Applying the watch XP recalculation: the plan the admin saw, a full backup first, every
player written in one transaction, one apply at a time and by an admin only. A plan that
changed and the failures have their own file."""
import asyncio

import pytest

from models.user import User
from services.portal import daily_digest, daily_digest_sources
from services.portal.admin_users_constants import (
    ACTION_DEBUG_WATCH_XP_RECALC,
    ACTION_DEBUG_WATCH_XP_RECALC_PLAYER,
)
from services.portal.xp import completion_reference
from services.portal.zone_correction import _run as zone_run
from tests._watch_xp_apply_helpers import (
    APPLY,
    ARCHIVE,
    HOUR,
    SIMULATE,
    audit_rows,
    confirmation,
    fake_backups,
    ledger_rows,
    profile_of,
    two_players,
)
from tests._watch_xp_helpers import T, account
from tests._watch_xp_recalc_helpers import give, sign_in_as, sitting

pytestmark = pytest.mark.asyncio


@pytest.fixture
def backups(monkeypatch):
    return fake_backups(monkeypatch)


async def test_apply_writes_the_rows_at_their_date_and_journals_each_player(client, db_session, backups):
    db = db_session
    ids = await two_players(client, db)
    alice, bob = ids["alice"], ids["bob"]
    daily_digest._cache_set(alice, "2026-03-08", "fr", {"cached": True})
    confirmed = await confirmation(client)

    resp = await client.post(APPLY, json=confirmed)

    assert resp.status_code == 200, resp.text
    assert resp.json() == {
        "plan": confirmed["plan"], "backup": ARCHIVE,
        "applied": {"players": 2, "rows_deleted": 1, "rows_inserted": 2},
    }
    assert backups[0] == ["watch_xp_recalc"]
    film, episode = completion_reference("MOVIE-1", ids["film"]), completion_reference("EP-1", ids["episode"])
    assert await ledger_rows(db) == {
        alice: [("daily_login", "2026-03-07", 2, T - 2 * HOUR), ("watch_movie", film, 40, T - HOUR)],
        bob: [("watch_episode", episode, 15, T + HOUR)],
    }
    # XP: before, less what went, plus what came; the 270 from before the ledger stay.
    assert [((p := await profile_of(db, user_id)).xp, p.level) for user_id in (alice, bob)] == [(312, 2), (15, 1)]
    assert daily_digest._digest_cache == {}

    audits = await audit_rows(db)
    players = {row.target_user_id: row.payload for row in audits[ACTION_DEBUG_WATCH_XP_RECALC_PLAYER]}
    assert players[alice] == {
        "xp": [282, 312], "level": [1, 2],
        "undo": {
            "deleted": [{
                "action": "watch_movie", "reference": "MOVIE-9:2026-03-07", "xp": 10,
                "created_at": (T - 2 * HOUR).isoformat(),
            }],
            "inserted": [film],
        },
    }
    assert players[bob]["undo"] == {"deleted": [], "inserted": [episode]}
    (overall,) = audits[ACTION_DEBUG_WATCH_XP_RECALC]
    assert overall.target_user_id is None
    assert overall.payload == {
        "as_of": confirmed["as_of"], "plan": confirmed["plan"], "backup": ARCHIVE,
        "players": 2, "rows_deleted": 1, "rows_inserted": 2,
    }


async def test_a_digest_built_across_the_apply_is_not_cached(client, db_session, backups, monkeypatch):
    db = db_session
    ids = await two_players(client, db)
    confirmed = await confirmation(client)
    monkeypatch.setattr(daily_digest, "_digest_cache", {})
    reading, resume = asyncio.Event(), asyncio.Event()
    closest = daily_digest_sources.closest_achievement

    async def held(*args, **kwargs):
        reading.set()
        await asyncio.wait_for(resume.wait(), 10)
        return await closest(*args, **kwargs)

    # Alice's digest reads her profile, then waits on a source while the apply commits.
    monkeypatch.setattr(daily_digest_sources, "closest_achievement", held)
    digest = asyncio.create_task(daily_digest.build_digest(db, await db.get(User, ids["alice"])))
    await asyncio.wait_for(reading.wait(), 10)
    resp = await client.post(APPLY, json=confirmed)
    resume.set()
    built = await asyncio.wait_for(digest, 10)

    assert resp.status_code == 200, resp.text
    assert (built["level"]["xp"], (await profile_of(db, ids["alice"])).xp) == (282, 312)
    assert daily_digest._digest_cache == {}


async def test_a_second_run_finds_nothing_and_backs_nothing_up(client, db_session, backups):
    await two_players(client, db_session)
    assert (await client.post(APPLY, json=await confirmation(client))).status_code == 200

    again = (await client.get(SIMULATE)).json()
    assert again["players_changed"] == 0
    resp = await client.post(APPLY, json={"as_of": again["as_of"], "plan": again["plan"]})

    assert resp.json() == {
        "plan": again["plan"], "backup": None, "applied": {"players": 0, "rows_deleted": 0, "rows_inserted": 0},
    }
    assert backups[0] == ["watch_xp_recalc"]


async def test_a_moment_without_zone_is_read_as_utc(client, db_session, backups):
    await two_players(client, db_session)
    confirmed = await confirmation(client)
    naive = confirmed["as_of"].removesuffix("+00:00")
    assert naive != confirmed["as_of"]

    resp = await client.post(APPLY, json={**confirmed, "as_of": naive})

    assert resp.status_code == 200, resp.text
    assert resp.json()["applied"]["players"] == 2


async def test_xp_never_falls_below_zero(client, db_session, backups):
    db = db_session
    await two_players(client, db)
    carol = await account(db, "carol")
    await sitting(db, "carol", "MOVIE-8", T - 5 * HOUR)
    await give(db, carol, "watch_movie", "MOVIE-8:2026-03-07", 25, T - 4 * HOUR)
    profile = await profile_of(db, carol)
    profile.xp = 5  # set lower by hand: the profile holds less than the 25 that go
    await db.commit()
    simulated = (await client.get(SIMULATE)).json()

    resp = await client.post(APPLY, json={"as_of": simulated["as_of"], "plan": simulated["plan"]})

    assert resp.status_code == 200, resp.text
    shown = next(row for row in simulated["rows"] if row["user_id"] == carol)
    profile = await profile_of(db, carol)
    assert (shown["xp"], shown["xp_after"], profile.xp, profile.level) == (5, 0, 0, 1)


async def test_an_apply_is_refused_while_a_time_zone_correction_runs(client, db_session, backups):
    await two_players(client, db_session)
    confirmed = await confirmation(client)

    async with zone_run._apply_lock:
        # Bounded: an apply that waited for the lock instead of refusing would hang the test.
        resp = await asyncio.wait_for(client.post(APPLY, json=confirmed), timeout=10)

    assert (resp.status_code, resp.json()["detail"]) == (409, "already_running")
    assert backups[0] == []


async def test_a_viewer_cannot_apply(client, db_session):
    await sign_in_as(client, db_session, "bob", "viewer")

    assert (await client.post(APPLY, json={"as_of": T.isoformat(), "plan": "x"})).status_code == 403


async def test_unknown_fields_are_refused(client, db_session, backups):
    await two_players(client, db_session)

    assert (await client.post(APPLY, json={**await confirmation(client), "force": True})).status_code == 422
