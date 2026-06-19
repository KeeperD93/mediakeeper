"""Admin debug tools — XP/level/achievement editing endpoints.

Auth scope: every endpoint requires the admin role (``require_admin``)
so a regular viewer hits 403.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from models.portal.achievement import UserAchievement
from models.portal.xp_ledger import XpLedger
from services.portal.achievements import seed_achievements
from services.portal.xp import xp_for_level
from tests._portal_profile_helpers import (
    PORTAL_COOKIE, make_portal_user, portal_token,
)


async def _admin_client(client, db_session):
    admin, _ = await make_portal_user(
        db_session, username="admin", display_name="admin", role="admin",
    )
    client.cookies.set(PORTAL_COOKIE, portal_token(admin.username))
    return admin


# ─── grant XP ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_debug_achievements_reports_computed_meta_threshold(client, db_session):
    """The catalogue picker reports the real computed threshold for meta
    achievements (same rule as the DB seed), not the META_DEFS placeholder,
    without relying on a seed-time mutation of the in-memory defs."""
    from services.portal.achievement_defs import (
        ACHIEVEMENT_DEFS,
        META_TARGET_CATEGORY,
        achievements_for_category,
    )
    await _admin_client(client, db_session)
    meta = next(
        (
            d for d in ACHIEVEMENT_DEFS
            if d.get("condition_type") == "meta" and META_TARGET_CATEGORY.get(d["id"])
        ),
        None,
    )
    assert meta is not None

    resp = await client.get("/api/portal/admin/debug/achievements")
    assert resp.status_code == 200, resp.text
    items = {it["id"]: it for it in resp.json()["items"]}
    expected = max(1, len(achievements_for_category(META_TARGET_CATEGORY[meta["id"]])))
    assert items[meta["id"]]["threshold"] == expected


@pytest.mark.asyncio
async def test_grant_xp_positive_levels_up(client, db_session):
    await _admin_client(client, db_session)
    target, tp = await make_portal_user(db_session, username="alice")
    tp.xp = 0
    tp.level = 0
    db_session.add(tp)
    await db_session.commit()

    resp = await client.post(
        "/api/portal/admin/debug/grant-xp",
        json={"user_id": target.id, "amount": 250, "note": "boost"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["xp"] == 250
    # xp_for_level(1)=100, xp_for_level(2)=300 → 250 XP lands at level 1.
    assert body["level"] == 1
    assert body["leveled_up"] is True

    ledger = (await db_session.execute(
        select(XpLedger).where(XpLedger.user_id == target.id)
    )).scalars().all()
    assert any(row.action == "admin_grant" for row in ledger)


@pytest.mark.asyncio
async def test_grant_xp_negative_clamps_to_zero(client, db_session):
    await _admin_client(client, db_session)
    target, tp = await make_portal_user(db_session, username="alice")
    tp.xp = 100
    db_session.add(tp)
    await db_session.commit()

    resp = await client.post(
        "/api/portal/admin/debug/grant-xp",
        json={"user_id": target.id, "amount": -500},
    )
    assert resp.status_code == 200
    assert resp.json()["xp"] == 0


@pytest.mark.asyncio
async def test_grant_xp_user_not_found(client, db_session):
    await _admin_client(client, db_session)
    resp = await client.post(
        "/api/portal/admin/debug/grant-xp",
        json={"user_id": 99999, "amount": 100},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_grant_xp_requires_admin(client, db_session):
    viewer, _ = await make_portal_user(db_session, username="alice")
    target, _ = await make_portal_user(db_session, username="bob")
    client.cookies.set(PORTAL_COOKIE, portal_token(viewer.username))

    resp = await client.post(
        "/api/portal/admin/debug/grant-xp",
        json={"user_id": target.id, "amount": 100},
    )
    assert resp.status_code == 403


# ─── set level ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_set_level_aligns_xp_to_floor(client, db_session):
    await _admin_client(client, db_session)
    target, _ = await make_portal_user(db_session, username="alice")

    resp = await client.post(
        "/api/portal/admin/debug/set-level",
        json={"user_id": target.id, "level": 10},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["level"] == 10
    assert body["xp"] == xp_for_level(10)


@pytest.mark.asyncio
async def test_set_level_can_demote(client, db_session):
    await _admin_client(client, db_session)
    target, tp = await make_portal_user(db_session, username="alice")
    tp.level = 30
    tp.xp = xp_for_level(30)
    db_session.add(tp)
    await db_session.commit()

    resp = await client.post(
        "/api/portal/admin/debug/set-level",
        json={"user_id": target.id, "level": 5},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["level"] == 5
    assert body["xp"] == xp_for_level(5)


# ─── achievements ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_unlock_and_lock_achievement(client, db_session):
    await seed_achievements(db_session)
    await _admin_client(client, db_session)
    target, _ = await make_portal_user(db_session, username="alice")

    # Pick the first non-secret achievement defined in defs.
    from services.portal.achievement_defs import ACHIEVEMENT_DEFS
    pick = next(d for d in ACHIEVEMENT_DEFS if not d.get("secret"))

    resp = await client.post(
        "/api/portal/admin/debug/unlock-achievement",
        json={"user_id": target.id, "achievement_id": pick["id"]},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["unlocked"] is True

    row = (await db_session.execute(
        select(UserAchievement).where(
            UserAchievement.user_id == target.id,
            UserAchievement.achievement_id == pick["id"],
        )
    )).scalar_one()
    assert row.unlocked is True

    # Locking removes the row entirely.
    resp = await client.post(
        "/api/portal/admin/debug/lock-achievement",
        json={"user_id": target.id, "achievement_id": pick["id"]},
    )
    assert resp.status_code == 200
    assert resp.json()["unlocked"] is False

    row_after = (await db_session.execute(
        select(UserAchievement).where(
            UserAchievement.user_id == target.id,
            UserAchievement.achievement_id == pick["id"],
        )
    )).scalar_one_or_none()
    assert row_after is None


@pytest.mark.asyncio
async def test_unlock_achievement_unknown_id(client, db_session):
    await seed_achievements(db_session)
    await _admin_client(client, db_session)
    target, _ = await make_portal_user(db_session, username="alice")

    resp = await client.post(
        "/api/portal/admin/debug/unlock-achievement",
        json={"user_id": target.id, "achievement_id": "does_not_exist"},
    )
    assert resp.status_code == 404


# ─── pickers ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_debug_users_picker_includes_admin(client, db_session):
    await _admin_client(client, db_session)
    await make_portal_user(db_session, username="alice")

    resp = await client.get("/api/portal/admin/debug/users")
    assert resp.status_code == 200
    items = resp.json()["items"]
    usernames = [it["username"] for it in items]
    assert "admin" in usernames
    assert "alice" in usernames


@pytest.mark.asyncio
async def test_debug_achievements_catalogue(client, db_session):
    await _admin_client(client, db_session)
    resp = await client.get("/api/portal/admin/debug/achievements")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) > 0
    # Shape contract for the picker.
    sample = items[0]
    for key in ("id", "name_key", "category", "tier", "secret"):
        assert key in sample


# ─── audit trail (#418) ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_grant_xp_records_audit(client, db_session):
    from models.portal.audit import AdminAuditLog

    admin = await _admin_client(client, db_session)
    target, _ = await make_portal_user(db_session, username="audit_target")

    resp = await client.post(
        "/api/portal/admin/debug/grant-xp",
        json={"user_id": target.id, "amount": 50},
    )
    assert resp.status_code == 200, resp.text

    rows = (await db_session.execute(
        select(AdminAuditLog).where(AdminAuditLog.action == "debug.xp_granted")
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].admin_user_id == admin.id
    assert rows[0].target_user_id == target.id


@pytest.mark.asyncio
async def test_reset_achievement_for_all_records_audit(client, db_session):
    from models.portal.achievement import Achievement
    from models.portal.audit import AdminAuditLog

    admin = await _admin_client(client, db_session)
    await seed_achievements(db_session)
    ach_id = (await db_session.execute(select(Achievement.id).limit(1))).scalar_one()

    resp = await client.post(
        "/api/portal/admin/debug/reset-achievement-for-all",
        json={"achievement_id": ach_id},
    )
    assert resp.status_code == 200, resp.text

    rows = (await db_session.execute(
        select(AdminAuditLog).where(
            AdminAuditLog.action == "debug.achievement_reset_all"
        )
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].admin_user_id == admin.id
    # Multi-user mutation → no single target.
    assert rows[0].target_user_id is None
