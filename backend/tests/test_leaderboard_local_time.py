"""The leaderboard, its past day and its trophies follow the saved zone, on every surface."""
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from constants.leaderboard import LeaderboardPeriod as Period
from models.portal.achievement import Achievement, UserAchievement
from models.portal.xp_ledger import XpLedger
from services.instance_time import INSTANCE_TIMEZONE_KEY
from services.portal import daily_digest_sources, profile_stats_ranking
from services.portal.profile_stats_ranking import (
    compute_leaderboard_only,
    compute_ranking,
)
from services.settings import set_setting
from tests._portal_profile_helpers import PORTAL_COOKIE, make_portal_user, portal_token

PARIS = ZoneInfo("Europe/Paris")
URL = "/api/portal/achievements/leaderboard/activity"


def _utc(year: int, month: int, day: int, *clock: int) -> datetime:
    return datetime(year, month, day, *clock, tzinfo=UTC)


# 00:30 on Wednesday in Paris, still Tuesday in UTC.
JUST_AFTER_PARIS_MIDNIGHT = _utc(2026, 11, 3, 23, 30)
PARIS_MIDNIGHT = _utc(2026, 11, 3, 23)


def _freeze(monkeypatch, moment: datetime) -> None:
    class _Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            return moment

    monkeypatch.setattr(profile_stats_ranking, "datetime", _Frozen)


def _row(user, xp: int, created_at: datetime) -> XpLedger:
    return XpLedger(
        user_id=user.id, action="watch_movie", reference=f"{xp}-{created_at}", xp=xp,
        created_at=created_at,
    )


async def _add(db, *rows) -> None:
    db.add_all(rows)
    await db.commit()


async def _players(db, *names: str) -> list:
    return [(await make_portal_user(db, username=name))[0] for name in names]


def _xp(items: list[dict]) -> list[tuple[int, int]]:
    return [(item["user_id"], item["period_xp"]) for item in items]


@pytest.mark.asyncio
async def test_the_day_starts_at_midnight_in_the_saved_zone(db_session, monkeypatch):
    alice, bob = await _players(db_session, "alice", "bob")
    await _add(
        db_session,
        _row(alice, 10, PARIS_MIDNIGHT),
        _row(bob, 20, PARIS_MIDNIGHT - timedelta(seconds=1)),
    )
    _freeze(monkeypatch, JUST_AFTER_PARIS_MIDNIGHT)

    before = await compute_leaderboard_only(db_session, period=Period.TODAY, lang="fr")
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")
    after = await compute_leaderboard_only(db_session, period=Period.TODAY, lang="fr")

    assert _xp(before["items"]) == [(bob.id, 20), (alice.id, 10)]
    assert before["stats"]["period_label"] == "Mardi 3 novembre"
    assert _xp(after["items"]) == [(alice.id, 10)]
    assert after["stats"]["total_xp"] == 10
    assert after["stats"]["period_label"] == "Mercredi 4 novembre"


@pytest.mark.asyncio
async def test_the_previous_day_ends_at_midnight_in_the_saved_zone(db_session, monkeypatch):
    """Bob was first on Tuesday in Paris: he led until 22:59 UTC, not until 23:59."""
    alice, bob = await _players(db_session, "alice", "bob")
    await _add(
        db_session,
        _row(alice, 10, PARIS_MIDNIGHT),
        _row(bob, 5, PARIS_MIDNIGHT),
        _row(bob, 20, PARIS_MIDNIGHT - timedelta(hours=1)),
        _row(alice, 50, PARIS_MIDNIGHT + timedelta(minutes=5)),
    )
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")
    _freeze(monkeypatch, JUST_AFTER_PARIS_MIDNIGHT)

    body = await compute_leaderboard_only(db_session, period=Period.TODAY)

    assert _xp(body["items"]) == [(alice.id, 60), (bob.id, 5)]
    # Alice was not ranked on Tuesday, so she has no move; Bob went from 1st to 2nd.
    assert [item["movement"] for item in body["items"]] == [0, -1]


@pytest.mark.asyncio
async def test_trophies_follow_the_day_of_the_saved_zone(db_session, monkeypatch):
    alice, = await _players(db_session, "alice")
    db_session.add_all([
        Achievement(
            id=trophy, category="test", name_key="portal.achievements.test",
            description_key="portal.achievements.test_desc", icon="Trophy", condition_type="test",
        )
        for trophy in ("today", "yesterday")
    ])
    await _add(
        db_session,
        UserAchievement(
            user_id=alice.id, achievement_id="today", progress=1, unlocked=True,
            unlocked_at=PARIS_MIDNIGHT, notified=False,
        ),
        UserAchievement(
            user_id=alice.id, achievement_id="yesterday", progress=1, unlocked=True,
            unlocked_at=PARIS_MIDNIGHT - timedelta(seconds=1), notified=False,
        ),
        _row(alice, 10, PARIS_MIDNIGHT),
    )
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")
    _freeze(monkeypatch, JUST_AFTER_PARIS_MIDNIGHT)

    body = await compute_leaderboard_only(db_session, period=Period.TODAY)

    assert body["stats"]["total_trophies"] == 1
    assert body["items"][0]["trophies_won"] == 1


@pytest.mark.asyncio
async def test_the_month_starts_and_counts_down_in_the_saved_zone(db_session, monkeypatch):
    alice, bob = await _players(db_session, "alice", "bob")
    first_of_november = _utc(2026, 10, 31, 23)
    await _add(
        db_session,
        _row(alice, 10, first_of_november),
        _row(bob, 20, first_of_november - timedelta(seconds=1)),
    )
    _freeze(monkeypatch, first_of_november + timedelta(minutes=30))

    before = await compute_leaderboard_only(db_session, period=Period.MONTH)
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")
    after = await compute_leaderboard_only(db_session, period=Period.MONTH)

    assert before["stats"]["days_remaining"] == 0
    assert before["stats"]["days_in_month"] == 31
    assert before["stats"]["period_label"] == "Octobre 2026"
    assert _xp(after["items"]) == [(alice.id, 10)]
    assert after["stats"]["days_remaining"] == 29
    assert after["stats"]["days_in_month"] == 30
    assert after["stats"]["period_label"] == "Novembre 2026"


@pytest.mark.asyncio
async def test_the_last_seven_days_stay_a_duration_across_a_clock_change(db_session, monkeypatch):
    """Seven days before 12:00 UTC is 12:00 UTC: on the Paris clock it would read 11:00 UTC."""
    alice, = await _players(db_session, "alice")
    now = _utc(2026, 10, 28, 12)
    await _add(
        db_session,
        _row(alice, 5, _utc(2026, 10, 21, 12, 30)),
        _row(alice, 7, _utc(2026, 10, 21, 11, 30)),
    )
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")
    _freeze(monkeypatch, now)

    body = await compute_leaderboard_only(
        db_session, period=Period.MONTH, viewer_user_id=alice.id,
    )

    assert body["stats"]["my_xp"] == 12
    assert body["stats"]["my_delta_week"] == 5


@pytest.mark.asyncio
@pytest.mark.parametrize(("period", "label", "days", "month_length"), [
    (Period.TODAY, "Mercredi 4 novembre", None, None),
    (Period.WEEK, "Du 2 au 8 novembre", None, None),
    (Period.MONTH, "Novembre 2026", 26, 30),
])
async def test_a_period_without_activity_is_named_in_the_saved_zone(
    db_session, monkeypatch, period, label, days, month_length,
):
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")
    _freeze(monkeypatch, JUST_AFTER_PARIS_MIDNIGHT)

    body = await compute_leaderboard_only(db_session, period=period)

    assert body["items"] == []
    assert body["stats"]["period_label"] == label
    assert body["stats"]["days_remaining"] == days
    assert body["stats"]["days_in_month"] == month_length


@pytest.mark.asyncio
async def test_a_failed_leaderboard_is_named_with_the_zone_it_had_read(db_session, monkeypatch):
    async def fail(db):
        raise RuntimeError("database down")

    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")
    monkeypatch.setattr(profile_stats_ranking, "excluded_from_leaderboard", fail)
    _freeze(monkeypatch, JUST_AFTER_PARIS_MIDNIGHT)

    body = await compute_leaderboard_only(db_session, period=Period.TODAY)

    assert body["items"] == []
    assert body["stats"]["period_label"] == "Mercredi 4 novembre"


@pytest.mark.asyncio
async def test_a_failed_read_of_the_zone_leaves_the_utc_calendar(db_session, monkeypatch):
    async def fail(db):
        raise RuntimeError("database down")

    monkeypatch.setattr(profile_stats_ranking, "get_instance_zone", fail)
    _freeze(monkeypatch, JUST_AFTER_PARIS_MIDNIGHT)

    body = await compute_leaderboard_only(db_session, period=Period.TODAY)

    assert body["items"] == []
    assert body["stats"]["period_label"] == "Mardi 3 novembre"


@pytest.mark.asyncio
async def test_the_profile_ranking_cuts_the_month_in_the_zone_it_receives(db_session, monkeypatch):
    alice, bob = await _players(db_session, "alice", "bob")
    first_of_november = _utc(2026, 10, 31, 23)
    await _add(
        db_session,
        _row(alice, 10, first_of_november),
        _row(bob, 20, first_of_november - timedelta(seconds=1)),
    )
    _freeze(monkeypatch, first_of_november + timedelta(minutes=30))

    in_utc = await compute_ranking(db_session, alice, zone=UTC)
    in_paris = await compute_ranking(db_session, alice, zone=PARIS)

    assert (in_utc["position"], in_utc["total"], in_utc["movement"]) == (2, 2, 0)
    assert (in_paris["position"], in_paris["total"], in_paris["movement"]) == (1, 1, 0)
    assert _xp(in_paris["leaderboard"]) == [(alice.id, 10)]


@pytest.mark.asyncio
async def test_the_digest_ranking_reads_the_saved_zone(db_session, monkeypatch):
    alice, bob = await _players(db_session, "alice", "bob")
    first_of_november = _utc(2026, 10, 31, 23)
    await _add(
        db_session,
        _row(alice, 10, first_of_november),
        _row(bob, 20, first_of_november - timedelta(seconds=1)),
    )
    _freeze(monkeypatch, first_of_november + timedelta(minutes=30))

    assert (await daily_digest_sources.ranking_snapshot(db_session, alice))["position"] == 2
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")
    assert (await daily_digest_sources.ranking_snapshot(db_session, alice))["position"] == 1


@pytest.mark.asyncio
async def test_the_public_profile_rank_reads_the_saved_zone(client, db_session, monkeypatch):
    alice, bob = await _players(db_session, "alice", "bob")
    first_of_november = _utc(2026, 10, 31, 23)
    await _add(
        db_session,
        _row(alice, 10, first_of_november),
        _row(bob, 20, first_of_november - timedelta(seconds=1)),
    )
    _freeze(monkeypatch, first_of_november + timedelta(minutes=30))
    client.cookies.set(PORTAL_COOKIE, portal_token(alice.username))
    url = f"/api/portal/profiles/by-user-id/{alice.id}/public"

    assert (await client.get(url)).json()["ranking"]["position"] == 2
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")
    assert (await client.get(url)).json()["ranking"]["position"] == 1


@pytest.mark.asyncio
async def test_the_leaderboard_route_serves_the_saved_zone(client, db_session, monkeypatch):
    alice, = await _players(db_session, "alice")
    await _add(db_session, _row(alice, 10, PARIS_MIDNIGHT))
    await set_setting(db_session, INSTANCE_TIMEZONE_KEY, "Europe/Paris")
    _freeze(monkeypatch, JUST_AFTER_PARIS_MIDNIGHT)
    client.cookies.set(PORTAL_COOKIE, portal_token(alice.username))

    resp = await client.get(URL, params={"period": "today"})

    assert resp.status_code == 200
    assert resp.json()["stats"]["period_label"] == "Mercredi 4 novembre"
    assert _xp(resp.json()["items"]) == [(alice.id, 10)]
