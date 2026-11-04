"""The ranking follows the chosen period on every figure it shows.

Rows sit exactly on the bounds: the first second of a period counts, the one
before it belongs to the previous period.
"""
from datetime import UTC, datetime, timedelta

import pytest

from constants.leaderboard import LeaderboardPeriod as Period
from models.portal.achievement import Achievement, UserAchievement
from models.portal.xp_ledger import XpLedger
from services.portal._leaderboard_periods import period_bounds, period_label
from tests._portal_profile_helpers import PORTAL_COOKIE, make_portal_user, portal_token

URL = "/api/portal/achievements/leaderboard/activity"
DATED_PERIODS = [Period.TODAY, Period.WEEK, Period.MONTH]
SHORT_PERIODS = [Period.TODAY, Period.WEEK, Period.ALL]
ONE_SECOND = timedelta(seconds=1)


def _bounds(period: Period):
    return period_bounds(period, datetime.now(UTC))


def _row(user_id: int, xp: int, created_at: datetime, action: str = "watch_movie") -> XpLedger:
    return XpLedger(
        user_id=user_id, action=action, reference=f"{action}-{xp}-{created_at}", xp=xp,
        created_at=created_at,
    )


async def _add(db_session, *rows: XpLedger) -> None:
    db_session.add_all(rows)
    await db_session.commit()


async def _add_trophy(db_session, user_id: int, trophy_id: str, unlocked_at: datetime | None):
    db_session.add_all([
        Achievement(
            id=trophy_id, category="test", name_key="portal.achievements.test",
            description_key="portal.achievements.test_desc", icon="Trophy", condition_type="test",
        ),
        UserAchievement(
            user_id=user_id, achievement_id=trophy_id, progress=1,
            unlocked=unlocked_at is not None, unlocked_at=unlocked_at, notified=False,
        ),
    ])
    await db_session.commit()


async def _get(client, viewer, period: Period | str, **params) -> dict:
    client.cookies.set(PORTAL_COOKIE, portal_token(viewer.username))
    resp = await client.get(URL, params={"period": period, **params})
    assert resp.status_code == 200
    return resp.json()


@pytest.mark.asyncio
@pytest.mark.parametrize("period", DATED_PERIODS)
async def test_a_period_starts_at_its_first_second(client, db_session, period):
    alice, _ = await make_portal_user(db_session, username="alice")
    start = _bounds(period).start
    await _add(db_session, _row(alice.id, 10, start), _row(alice.id, 5, start - ONE_SECOND))

    body = await _get(client, alice, period)

    assert [row["period_xp"] for row in body["items"]] == [10]
    assert body["stats"]["total_xp"] == 10
    assert body["stats"]["my_xp"] == 10


@pytest.mark.asyncio
async def test_all_time_adds_the_whole_ledger_but_activity_only(client, db_session):
    alice, _ = await make_portal_user(db_session, username="alice")
    long_ago = datetime(2021, 3, 4, tzinfo=UTC)
    await _add(
        db_session,
        _row(alice.id, 7, long_ago),
        _row(alice.id, 3, datetime.now(UTC)),
        _row(alice.id, 1000, long_ago, action="achievement_unlocked"),
        _row(alice.id, 500, long_ago, action="admin_grant"),
    )

    body = await _get(client, alice, Period.ALL)

    assert [row["period_xp"] for row in body["items"]] == [10]
    assert body["stats"]["total_xp"] == 10


@pytest.mark.asyncio
@pytest.mark.parametrize("period", DATED_PERIODS)
async def test_arrows_compare_with_the_previous_period_and_only_it(client, db_session, period):
    """Bob was second last period: his older XP and his XP of today do not count there."""
    alice, _ = await make_portal_user(db_session, username="alice")
    bob, _ = await make_portal_user(db_session, username="bob")
    bounds = _bounds(period)
    await _add(
        db_session,
        _row(bob.id, 1000, bounds.previous_start - ONE_SECOND),
        _row(alice.id, 100, bounds.start - ONE_SECOND),
        _row(bob.id, 50, bounds.previous_start),
        _row(alice.id, 100, bounds.start),
        _row(bob.id, 200, bounds.start),
    )

    body = await _get(client, alice, period)

    assert {row["user_id"]: row["movement"] for row in body["items"]} == {bob.id: 1, alice.id: -1}


@pytest.mark.asyncio
async def test_all_time_has_no_arrow(client, db_session):
    alice, _ = await make_portal_user(db_session, username="alice")
    await _add(db_session, _row(alice.id, 10, datetime.now(UTC)))

    body = await _get(client, alice, Period.ALL)

    assert body["items"][0]["movement"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize("period", DATED_PERIODS)
async def test_a_newcomer_of_the_period_stays_flat(client, db_session, period):
    alice, _ = await make_portal_user(db_session, username="alice")
    await _add(db_session, _row(alice.id, 10, _bounds(period).start))

    body = await _get(client, alice, period)

    assert body["items"][0]["movement"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("period", DATED_PERIODS)
async def test_trophies_follow_the_period(client, db_session, period):
    alice, _ = await make_portal_user(db_session, username="alice")
    start = _bounds(period).start
    await _add(db_session, _row(alice.id, 10, start))
    await _add_trophy(db_session, alice.id, "in_period", start)
    await _add_trophy(db_session, alice.id, "before_period", start - ONE_SECOND)
    await _add_trophy(db_session, alice.id, "in_progress", None)

    body = await _get(client, alice, period)

    assert body["items"][0]["trophies_won"] == 1
    assert body["stats"]["total_trophies"] == 1


@pytest.mark.asyncio
async def test_all_time_counts_every_trophy_ever_unlocked(client, db_session):
    alice, _ = await make_portal_user(db_session, username="alice")
    await _add(db_session, _row(alice.id, 10, datetime.now(UTC)))
    await _add_trophy(db_session, alice.id, "old", datetime(2021, 3, 4, tzinfo=UTC))
    await _add_trophy(db_session, alice.id, "recent", datetime.now(UTC))
    await _add_trophy(db_session, alice.id, "in_progress", None)

    body = await _get(client, alice, Period.ALL)

    assert body["items"][0]["trophies_won"] == 2
    assert body["stats"]["total_trophies"] == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("period", SHORT_PERIODS)
async def test_the_outlook_of_the_month_stays_on_the_month(client, db_session, period):
    alice, _ = await make_portal_user(db_session, username="alice")
    await _add(db_session, _row(alice.id, 10, datetime.now(UTC)))

    stats = (await _get(client, alice, period))["stats"]

    assert stats["days_remaining"] is None
    assert stats["days_in_month"] is None
    assert stats["my_delta_week"] is None
    assert stats["projected_end_rank"] is None
    assert stats["my_xp"] == 10


@pytest.mark.asyncio
async def test_the_month_keeps_its_outlook(client, db_session):
    alice, _ = await make_portal_user(db_session, username="alice")
    await _add(db_session, _row(alice.id, 10, datetime.now(UTC)))

    stats = (await _get(client, alice, Period.MONTH))["stats"]

    assert isinstance(stats["days_remaining"], int)
    assert stats["days_in_month"] in (28, 29, 30, 31)
    assert stats["my_delta_week"] == 10
    assert stats["projected_end_rank"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("period", list(Period))
async def test_a_viewer_outside_the_list_gets_their_row_for_the_period(client, db_session, period):
    alice, _ = await make_portal_user(db_session, username="alice")
    bob, _ = await make_portal_user(db_session, username="bob")
    now = datetime.now(UTC)
    await _add(db_session, _row(bob.id, 20, now), _row(alice.id, 10, now))

    body = await _get(client, alice, period, limit=1)

    assert [row["user_id"] for row in body["items"]] == [bob.id]
    assert body["viewer_rank"] == 2
    assert body["viewer_entry"]["period_xp"] == 10
    assert body["viewer_entry"]["is_current_user"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("period", [Period.TODAY, Period.WEEK])
async def test_a_viewer_idle_in_the_period_has_no_rank(client, db_session, period):
    alice, _ = await make_portal_user(db_session, username="alice")
    bob, _ = await make_portal_user(db_session, username="bob")
    await _add(
        db_session,
        _row(alice.id, 500, _bounds(period).start - ONE_SECOND),
        _row(bob.id, 10, datetime.now(UTC)),
    )

    body = await _get(client, alice, period)

    assert [row["user_id"] for row in body["items"]] == [bob.id]
    assert body["viewer_rank"] is None
    assert body["viewer_entry"] is None
    assert body["stats"]["my_xp"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("period", list(Period))
async def test_excluded_accounts_stay_out_of_every_period(client, db_session, period):
    alice, _ = await make_portal_user(db_session, username="alice")
    gone, gone_profile = await make_portal_user(db_session, username="gone")
    gone_profile.account_active = False
    db_session.add(gone_profile)
    now = datetime.now(UTC)
    await _add(db_session, _row(alice.id, 10, now), _row(gone.id, 900, now))
    await _add_trophy(db_session, gone.id, "left_out", now)

    body = await _get(client, alice, period)

    assert [row["user_id"] for row in body["items"]] == [alice.id]
    assert body["stats"]["total_xp"] == 10
    assert body["stats"]["total_trophies"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("lang", ["fr", "en"])
@pytest.mark.parametrize("period", list(Period))
async def test_the_label_names_the_period_in_the_app_language(client, db_session, period, lang):
    alice, _ = await make_portal_user(db_session, username="alice")
    await _add(db_session, _row(alice.id, 10, datetime.now(UTC)))

    client.cookies.set(PORTAL_COOKIE, portal_token(alice.username))
    resp = await client.get(URL, params={"period": period}, headers={"X-MK-Locale": lang})

    assert resp.status_code == 200
    assert resp.json()["stats"]["period_label"] == period_label(period, datetime.now(UTC), lang)


@pytest.mark.asyncio
@pytest.mark.parametrize("period", SHORT_PERIODS)
async def test_a_period_without_activity_stays_empty_and_named(client, db_session, period):
    alice, _ = await make_portal_user(db_session, username="alice")

    body = await _get(client, alice, period)

    assert body["items"] == []
    assert body["viewer_rank"] is None
    assert body["stats"]["period_label"] == period_label(period, datetime.now(UTC), "fr")
    assert body["stats"]["total_players"] == 0
    assert body["stats"]["days_remaining"] is None
    assert body["stats"]["days_in_month"] is None


@pytest.mark.asyncio
async def test_no_period_means_the_month(client, db_session):
    alice, _ = await make_portal_user(db_session, username="alice")
    await _add(
        db_session,
        _row(alice.id, 10, _bounds(Period.MONTH).start),
        _row(alice.id, 5, _bounds(Period.MONTH).start - ONE_SECOND),
    )

    client.cookies.set(PORTAL_COOKIE, portal_token(alice.username))
    resp = await client.get(URL)

    assert resp.status_code == 200
    assert resp.json()["items"][0]["period_xp"] == 10


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [
    "", "MONTH", " month", "year", "month;drop", "0", pytest.param("é" * 300, id="very-long"),
])
async def test_an_unknown_period_is_refused(client, db_session, value):
    alice, _ = await make_portal_user(db_session, username="alice")

    client.cookies.set(PORTAL_COOKIE, portal_token(alice.username))
    resp = await client.get(URL, params={"period": value})

    assert resp.status_code == 422
