"""Coverage for the dedicated /portal/leaderboard page endpoint.

``GET /api/portal/achievements/leaderboard/activity`` returns the
top-N players by monthly XP by default — the source of truth for the premium
hero billboard + podium + ranks 4-100 table on /portal/leaderboard.
The endpoint shares its trust boundary with the profile mini-
leaderboard: any authenticated portal user can view it, while admin
/ soft-deleted / deactivated accounts stay excluded. The payload
also embeds viewer-aware stats (``viewer_rank``, ``viewer_entry``,
``stats``) consumed by the hero/stats-bar/my-rank cards.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from models.portal.xp_ledger import XpLedger
from services.portal._leaderboard_helpers import MONTH_LABELS_EN, MONTH_LABELS_FR
from tests._portal_profile_helpers import (
    PORTAL_COOKIE, make_portal_user, portal_token,
)


async def _grant_month_xp(db_session, user_id: int, xp: int, ref: str) -> None:
    db_session.add(XpLedger(user_id=user_id, action="watch_movie", reference=ref, xp=xp))
    await db_session.commit()


@pytest.mark.asyncio
async def test_monthly_leaderboard_returns_items(client, db_session):
    me, _ = await make_portal_user(db_session, username="alice")
    other, _ = await make_portal_user(db_session, username="bob")
    await _grant_month_xp(db_session, me.id, 1500, "month-alice")
    await _grant_month_xp(db_session, other.id, 800, "month-bob")

    client.cookies.set(PORTAL_COOKIE, portal_token(me.username))
    resp = await client.get("/api/portal/achievements/leaderboard/activity")
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    user_ids = [it["user_id"] for it in body["items"]]
    assert me.id in user_ids
    assert other.id in user_ids
    # Entries carry the leaderboard-card schema (rank + tier + period_xp).
    first = body["items"][0]
    for key in ("rank", "user_id", "display_name", "level", "tier", "title_key", "period_xp"):
        assert key in first
    # Premium payload exposes viewer-aware fields + stats.
    assert "viewer_rank" in body
    assert "viewer_entry" in body
    assert "stats" in body


@pytest.mark.asyncio
async def test_monthly_leaderboard_respects_limit(client, db_session):
    """``limit`` caps how many entries come back."""
    me, _ = await make_portal_user(db_session, username="alice")
    await _grant_month_xp(db_session, me.id, 100, "month-alice")
    for i in range(4):
        other, _ = await make_portal_user(db_session, username=f"bob{i}")
        await _grant_month_xp(db_session, other.id, 200 + i, f"month-bob{i}")

    client.cookies.set(PORTAL_COOKIE, portal_token(me.username))
    resp = await client.get("/api/portal/achievements/leaderboard/activity?limit=3")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 3


@pytest.mark.asyncio
async def test_monthly_leaderboard_rejects_overshoot_limit(client, db_session):
    me, _ = await make_portal_user(db_session, username="alice")
    client.cookies.set(PORTAL_COOKIE, portal_token(me.username))

    resp = await client.get("/api/portal/achievements/leaderboard/activity?limit=500")
    # FastAPI's Query(le=100) gates the upper bound — 500 is rejected
    # before the service runs.
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_monthly_leaderboard_excludes_local_admin_and_deactivated(client, db_session):
    """Local-only admin accounts (no Emby link), soft-deleted accounts
    and deactivated accounts must never appear in the public ranking
    — same exclusion contract as the profile mini-leaderboard."""
    me, _ = await make_portal_user(db_session, username="alice")
    # Production-shaped admin: local account, no emby_user_id. The
    # ``source != "emby"`` clause of _excluded_from_leaderboard pulls
    # it out of the ranking.
    local_admin, _ = await make_portal_user(
        db_session,
        username="admin",
        display_name="admin",
        role="admin",
        emby_user_id=None,
    )
    dead, dead_profile = await make_portal_user(db_session, username="zombie")
    dead_profile.account_active = False
    db_session.add(dead_profile)
    await db_session.commit()

    await _grant_month_xp(db_session, me.id, 100, "month-alice")
    await _grant_month_xp(db_session, local_admin.id, 99999, "month-admin")
    await _grant_month_xp(db_session, dead.id, 5000, "month-zombie")

    client.cookies.set(PORTAL_COOKIE, portal_token(me.username))
    resp = await client.get("/api/portal/achievements/leaderboard/activity")
    assert resp.status_code == 200
    user_ids = [it["user_id"] for it in resp.json()["items"]]
    assert me.id in user_ids
    assert local_admin.id not in user_ids
    assert dead.id not in user_ids


@pytest.mark.asyncio
async def test_monthly_leaderboard_requires_portal_auth(client, db_session):
    """No cookie → 401, even though the data is "public" for users."""
    client.cookies.clear()
    resp = await client.get("/api/portal/achievements/leaderboard/activity")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_monthly_leaderboard_viewer_in_top_marks_row(client, db_session):
    """Viewer present in top-N → row carries ``is_current_user=True``,
    no ``viewer_rank`` / ``viewer_entry`` (they're top-list redundancy)."""
    me, _ = await make_portal_user(db_session, username="alice")
    other, _ = await make_portal_user(db_session, username="bob")
    await _grant_month_xp(db_session, me.id, 1500, "month-alice")
    await _grant_month_xp(db_session, other.id, 500, "month-bob")

    client.cookies.set(PORTAL_COOKIE, portal_token(me.username))
    resp = await client.get("/api/portal/achievements/leaderboard/activity")
    assert resp.status_code == 200
    body = resp.json()

    my_row = next(it for it in body["items"] if it["user_id"] == me.id)
    assert my_row["is_current_user"] is True
    other_row = next(it for it in body["items"] if it["user_id"] == other.id)
    assert other_row["is_current_user"] is False
    assert body["viewer_rank"] is None
    assert body["viewer_entry"] is None


@pytest.mark.asyncio
async def test_monthly_leaderboard_viewer_outside_top_returns_entry(client, db_session):
    """Viewer out of top-N → ``viewer_rank`` / ``viewer_entry`` populated,
    and items rows keep ``is_current_user=False``."""
    me, _ = await make_portal_user(db_session, username="alice")
    await _grant_month_xp(db_session, me.id, 50, "month-alice")
    for i in range(3):
        other, _ = await make_portal_user(db_session, username=f"bob{i}")
        await _grant_month_xp(db_session, other.id, 1000 + i * 10, f"month-bob{i}")

    client.cookies.set(PORTAL_COOKIE, portal_token(me.username))
    resp = await client.get("/api/portal/achievements/leaderboard/activity?limit=2")
    assert resp.status_code == 200
    body = resp.json()

    user_ids = [it["user_id"] for it in body["items"]]
    assert me.id not in user_ids
    assert all(not it["is_current_user"] for it in body["items"])
    assert body["viewer_rank"] == 4  # 3 bobs ahead, me at #4
    assert body["viewer_entry"] is not None
    assert body["viewer_entry"]["user_id"] == me.id
    assert body["viewer_entry"]["period_xp"] == 50
    assert body["viewer_entry"]["is_current_user"] is True


@pytest.mark.asyncio
async def test_monthly_leaderboard_stats_schema(client, db_session):
    """Stats payload exposes the seven keys consumed by the live bar
    + viewer-aware tail (my_xp, my_delta_week, projected_end_rank)."""
    me, _ = await make_portal_user(db_session, username="alice")
    other, _ = await make_portal_user(db_session, username="bob")
    await _grant_month_xp(db_session, me.id, 800, "month-alice")
    await _grant_month_xp(db_session, other.id, 400, "month-bob")

    client.cookies.set(PORTAL_COOKIE, portal_token(me.username))
    resp = await client.get("/api/portal/achievements/leaderboard/activity")
    assert resp.status_code == 200
    stats = resp.json()["stats"]

    for key in (
        "period_label",
        "total_players",
        "total_xp",
        "days_remaining",
        "my_xp",
        "my_delta_week",
        "projected_end_rank",
    ):
        assert key in stats

    assert isinstance(stats["period_label"], str) and stats["period_label"]
    assert stats["total_players"] == 2
    assert stats["total_xp"] == 1200
    assert isinstance(stats["days_remaining"], int)
    assert stats["my_xp"] == 800
    # Fresh XpLedger rows fall inside the 7-day window → delta matches XP.
    assert stats["my_delta_week"] == 800
    assert stats["projected_end_rank"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(("headers", "labels"), [
    # A French browser that also lists English, as browsers commonly do.
    ({"Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7"}, MONTH_LABELS_FR),
    ({"X-MK-Locale": "fr", "Accept-Language": "en-US,en;q=0.9"}, MONTH_LABELS_FR),
    ({"X-MK-Locale": "en", "Accept-Language": "fr-FR,fr;q=0.9"}, MONTH_LABELS_EN),
    ({"Accept-Language": "en-US,en;q=0.9,fr;q=0.8"}, MONTH_LABELS_EN),
    ({}, MONTH_LABELS_FR),
    # A language the server does not write, and a header that is not a language.
    ({"X-MK-Locale": "de"}, MONTH_LABELS_FR),
    ({"X-MK-Locale": "<script>", "Accept-Language": "en"}, MONTH_LABELS_EN),
])
async def test_monthly_leaderboard_month_follows_the_app_language(
    client, db_session, headers, labels,
):
    me, _ = await make_portal_user(db_session, username="alice")
    await _grant_month_xp(db_session, me.id, 100, "month-alice")

    client.cookies.set(PORTAL_COOKIE, portal_token(me.username))
    resp = await client.get("/api/portal/achievements/leaderboard/activity", headers=headers)

    assert resp.status_code == 200
    now = datetime.now(UTC)
    assert resp.json()["stats"]["period_label"] == f"{labels[now.month]} {now.year}"
