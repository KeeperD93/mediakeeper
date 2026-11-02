"""The monthly ranking counts activity only, on every number it shows.

Trophy and admin XP still raise the level, but must stay out of the month
total, the player count, the weekly delta, the projection and the arrows.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from models.portal.xp_ledger import XpLedger
from services.portal.profile_stats_ranking import compute_ranking
from tests._portal_profile_helpers import (
    PORTAL_COOKIE, make_portal_user, portal_token,
)

MONTHLY_URL = "/api/portal/achievements/leaderboard/monthly"


def _previous_month() -> datetime:
    month_start = datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    return month_start - timedelta(days=1)


def _row(
    user_id: int, action: str, xp: int, created_at: datetime | None = None
) -> XpLedger:
    row = XpLedger(user_id=user_id, action=action, reference=f"{action}-{xp}", xp=xp)
    if created_at is not None:
        row.created_at = created_at
    return row


async def _add(db_session, *rows: XpLedger) -> None:
    db_session.add_all(rows)
    await db_session.commit()


async def _get_monthly(client, viewer) -> dict:
    client.cookies.set(PORTAL_COOKIE, portal_token(viewer.username))
    resp = await client.get(MONTHLY_URL)
    assert resp.status_code == 200
    return resp.json()


@pytest.mark.asyncio
async def test_every_figure_counts_each_activity_and_nothing_else(client, db_session):
    alice, _ = await make_portal_user(db_session, username="alice")
    bob, _ = await make_portal_user(db_session, username="bob")
    await _add(
        db_session,
        # Distinct powers of two: a missing action cannot go unnoticed.
        _row(alice.id, "watch_movie", 1),
        _row(alice.id, "watch_episode", 2),
        _row(alice.id, "daily_login", 4),
        _row(alice.id, "request_created", 8),
        _row(alice.id, "achievement_unlocked", 4800),
        _row(alice.id, "admin_grant", 900),
        _row(alice.id, "surprise_used", 0),
        _row(bob.id, "watch_movie", 100),
    )

    body = await _get_monthly(client, alice)

    assert [(e["user_id"], e["rank"], e["month_xp"]) for e in body["items"]] == [
        (bob.id, 1, 100),
        (alice.id, 2, 15),
    ]
    stats = body["stats"]
    assert stats["total_players"] == 2
    assert stats["total_xp_month"] == 115
    assert stats["my_xp_month"] == 15
    assert stats["my_delta_week"] == 15
    assert stats["projected_end_rank"] == 2


@pytest.mark.asyncio
async def test_rows_without_activity_do_not_make_a_player(client, db_session):
    alice, _ = await make_portal_user(db_session, username="alice")
    surprise, _ = await make_portal_user(db_session, username="surprise")
    trophy, _ = await make_portal_user(db_session, username="trophy")
    granted, _ = await make_portal_user(db_session, username="granted")
    await _add(
        db_session,
        _row(alice.id, "watch_movie", 10),
        _row(surprise.id, "surprise_used", 0),
        _row(trophy.id, "achievement_unlocked", 500),
        _row(granted.id, "admin_grant", 500),
    )

    body = await _get_monthly(client, trophy)

    assert [e["user_id"] for e in body["items"]] == [alice.id]
    assert body["stats"]["total_players"] == 1
    assert body["stats"]["total_xp_month"] == 10
    assert body["stats"]["my_xp_month"] == 0
    assert body["stats"]["my_delta_week"] == 0
    assert body["viewer_rank"] is None
    assert body["viewer_entry"] is None


@pytest.mark.asyncio
async def test_month_with_only_trophies_leaves_an_empty_ranking(client, db_session):
    alice, _ = await make_portal_user(db_session, username="alice")
    await _add(db_session, _row(alice.id, "achievement_unlocked", 500))

    body = await _get_monthly(client, alice)

    assert body["items"] == []
    assert body["stats"]["total_players"] == 0
    assert body["stats"]["total_xp_month"] == 0


@pytest.mark.asyncio
async def test_admin_removal_does_not_lower_the_month(client, db_session):
    alice, _ = await make_portal_user(db_session, username="alice")
    await _add(
        db_session,
        _row(alice.id, "watch_movie", 100),
        _row(alice.id, "admin_grant", -5000),
    )

    body = await _get_monthly(client, alice)

    assert body["items"][0]["month_xp"] == 100
    assert body["stats"]["my_delta_week"] == 100


@pytest.mark.asyncio
async def test_arrows_compare_activity_with_activity(client, db_session):
    """A trophy last month put Bob first; on activity he was second."""
    alice, _ = await make_portal_user(db_session, username="alice")
    bob, _ = await make_portal_user(db_session, username="bob")
    last_month = _previous_month()
    await _add(
        db_session,
        _row(alice.id, "watch_movie", 100, last_month),
        _row(bob.id, "watch_movie", 50, last_month),
        _row(bob.id, "achievement_unlocked", 1000, last_month),
        _row(alice.id, "watch_episode", 100),
        _row(bob.id, "watch_episode", 200),
    )

    body = await _get_monthly(client, alice)

    movement = {e["user_id"]: e["movement"] for e in body["items"]}
    assert movement == {bob.id: 1, alice.id: -1}


@pytest.mark.asyncio
async def test_last_month_rows_stay_out_of_the_month_total(client, db_session):
    alice, _ = await make_portal_user(db_session, username="alice")
    await _add(
        db_session,
        _row(alice.id, "watch_movie", 70, _previous_month()),
        _row(alice.id, "watch_episode", 30),
    )

    body = await _get_monthly(client, alice)

    assert body["items"][0]["month_xp"] == 30


@pytest.mark.asyncio
async def test_ties_follow_user_id_whatever_the_insert_order(client, db_session):
    alice, _ = await make_portal_user(db_session, username="alice")
    bob, _ = await make_portal_user(db_session, username="bob")
    await _add(db_session, _row(bob.id, "daily_login", 2))
    await _add(db_session, _row(alice.id, "daily_login", 2))

    body = await _get_monthly(client, alice)

    assert [e["user_id"] for e in body["items"]] == sorted([alice.id, bob.id])


@pytest.mark.asyncio
async def test_profile_ranking_follows_the_same_rule(db_session):
    """The profile card, the public profile and the digest read compute_ranking."""
    alice, _ = await make_portal_user(db_session, username="alice")
    bob, _ = await make_portal_user(db_session, username="bob")
    trophy, _ = await make_portal_user(db_session, username="trophy")
    last_month = _previous_month()
    await _add(
        db_session,
        _row(alice.id, "watch_movie", 100, last_month),
        _row(bob.id, "watch_movie", 50, last_month),
        _row(bob.id, "achievement_unlocked", 1000, last_month),
        _row(alice.id, "watch_episode", 100),
        _row(alice.id, "achievement_unlocked", 5000),
        _row(bob.id, "watch_episode", 200),
        _row(trophy.id, "achievement_unlocked", 500),
    )

    ranking = await compute_ranking(db_session, alice)

    assert ranking["position"] == 2
    assert ranking["total"] == 2
    assert ranking["percentile"] == 100
    assert ranking["movement"] == -1
    assert [(e["user_id"], e["month_xp"]) for e in ranking["leaderboard"]] == [
        (bob.id, 200),
        (alice.id, 100),
    ]

    outside = await compute_ranking(db_session, trophy)

    assert outside["position"] == 0
    assert outside["percentile"] == 0
    assert all(e["user_id"] != trophy.id for e in outside["leaderboard"])
