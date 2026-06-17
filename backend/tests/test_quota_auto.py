"""Tests for the automatic request-quota engine (services.portal.quota_auto)."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from services.portal import quota_auto as qa


def test_compute_score_weights_and_caps():
    # Every signal is capped; plays weigh the most.
    counts = {"play": 100, "login": 100, "request": 100, "list": 100, "ticket": 100}
    assert qa.compute_score(counts) == pytest.approx(20 * 1.0 + 15 * 0.5 + 10 * 0.4 + 5 * 0.6 + 5 * 0.3)
    assert qa.compute_score({}) == 0


def test_compute_target_maps_to_band():
    assert qa.compute_target(0, 2, 15) == 2                       # idle -> floor
    assert qa.compute_target(qa._SCORE_FULL, 2, 15) == 15         # full -> ceiling
    assert qa.compute_target(qa._SCORE_FULL * 5, 2, 15) == 15     # over-full clamps
    assert 2 < qa.compute_target(qa._SCORE_FULL / 2, 2, 15) < 15


def test_next_cap_grant_decay_grace_clamp():
    # Grant: target above current rises by up_step.
    assert qa.next_cap(5, 12, days_idle=0, grace_days=14, up_step=2, down_step=1, lo=2, hi=15) == 7
    # Within grace: target below current but idle < grace -> hold (holiday-safe).
    assert qa.next_cap(10, 4, days_idle=5, grace_days=14, up_step=2, down_step=1, lo=2, hi=15) == 10
    # Past grace: decay by down_step.
    assert qa.next_cap(10, 4, days_idle=20, grace_days=14, up_step=2, down_step=1, lo=2, hi=15) == 9
    # Clamp to floor / ceiling.
    assert qa.next_cap(3, 2, days_idle=99, grace_days=14, up_step=2, down_step=1, lo=2, hi=15) == 2
    assert qa.next_cap(15, 20, days_idle=0, grace_days=14, up_step=2, down_step=1, lo=2, hi=15) == 15


def _seed_auto_quota(db_session, admin_user, **over):
    from models.portal.profile import UserProfile
    from models.portal.request import RequestQuota
    db_session.add(UserProfile(
        user_id=admin_user.id, display_name="Active", role="viewer",
        source="local", account_active=True,
    ))
    db_session.add(RequestQuota(
        user_id=admin_user.id, month="2026-06", max_allowed=over.get("max_allowed", 5),
        mode="auto", unlimited=False, auto_min=2, auto_max=15,
    ))


@pytest.mark.asyncio
async def test_recompute_grants_active_user(admin_user, db_session):
    from models.portal.login_history import UserLoginHistory
    from models.portal.request import RequestQuota

    _seed_auto_quota(db_session, admin_user)
    now = datetime.now(timezone.utc)
    for i in range(16):  # capped at 15 -> login score 7.5 -> target 6 > 5
        db_session.add(UserLoginHistory(
            user_id=admin_user.id, username="active", source="portal",
            success=True, created_at=now - timedelta(days=i % 25),
        ))
    await db_session.commit()

    res = await qa.recompute_auto_quotas(db_session, now=now)
    assert res == {"processed": 1, "changed": 1}

    refreshed = (await db_session.execute(
        select(RequestQuota).where(RequestQuota.user_id == admin_user.id)
    )).scalar_one()
    assert refreshed.max_allowed == 7  # 5 + up_step
    assert refreshed.last_recomputed_at is not None


@pytest.mark.asyncio
async def test_recompute_records_system_audit_on_grant(admin_user, db_session):
    """A cap change emits a system audit row (actor=None, source=auto) carrying
    the from/to and the grant/reduction direction — the auto branch's audit
    content differs from the admin path and must be pinned."""
    from models.portal.audit import AdminAuditLog
    from models.portal.login_history import UserLoginHistory
    from services.portal.admin_users_constants import ACTION_USER_QUOTA_CHANGED

    _seed_auto_quota(db_session, admin_user)
    now = datetime.now(timezone.utc)
    for i in range(16):
        db_session.add(UserLoginHistory(
            user_id=admin_user.id, username="active", source="portal",
            success=True, created_at=now - timedelta(days=i % 25),
        ))
    await db_session.commit()

    await qa.recompute_auto_quotas(db_session, now=now)

    audit = (await db_session.execute(
        select(AdminAuditLog).where(
            AdminAuditLog.target_user_id == admin_user.id,
            AdminAuditLog.action == ACTION_USER_QUOTA_CHANGED,
        )
    )).scalar_one()
    assert audit.admin_user_id is None  # system actor, not an admin
    assert audit.payload["source"] == "auto"
    assert audit.payload["direction"] == "grant"
    assert audit.payload["changed"]["max_allowed"] == {"from": 5, "to": 7}


@pytest.mark.asyncio
async def test_recompute_is_idempotent_within_guard(admin_user, db_session):
    from models.portal.login_history import UserLoginHistory
    from models.portal.request import RequestQuota

    _seed_auto_quota(db_session, admin_user)
    now = datetime.now(timezone.utc)
    for i in range(16):
        db_session.add(UserLoginHistory(
            user_id=admin_user.id, username="active", source="portal",
            success=True, created_at=now - timedelta(days=i % 25),
        ))
    await db_session.commit()

    await qa.recompute_auto_quotas(db_session, now=now)
    # Second pass moments later: the row is within the rerun guard -> skipped.
    res = await qa.recompute_auto_quotas(db_session, now=now + timedelta(minutes=5))
    assert res == {"processed": 0, "changed": 0}

    refreshed = (await db_session.execute(
        select(RequestQuota).where(RequestQuota.user_id == admin_user.id)
    )).scalar_one()
    assert refreshed.max_allowed == 7  # unchanged by the skipped pass


@pytest.mark.asyncio
async def test_recompute_disabled_is_noop(admin_user, db_session):
    from models.settings import Setting

    _seed_auto_quota(db_session, admin_user)
    db_session.add(Setting(key="quota.auto.enabled", value="false"))
    await db_session.commit()

    res = await qa.recompute_auto_quotas(db_session)
    assert res == {"skipped": "disabled"}


@pytest.mark.asyncio
async def test_recompute_decays_idle_user_past_grace(admin_user, db_session):
    from models.portal.request import RequestQuota

    # Cap above the floor, zero recent activity -> idle past grace -> decay.
    _seed_auto_quota(db_session, admin_user, max_allowed=10)
    await db_session.commit()

    res = await qa.recompute_auto_quotas(db_session, now=datetime.now(timezone.utc))
    assert res == {"processed": 1, "changed": 1}

    refreshed = (await db_session.execute(
        select(RequestQuota).where(RequestQuota.user_id == admin_user.id)
    )).scalar_one()
    assert refreshed.max_allowed == 9  # 10 - down_step


@pytest.mark.asyncio
async def test_recompute_skips_unlimited_auto_row(admin_user, db_session):
    from models.portal.profile import UserProfile
    from models.portal.request import RequestQuota

    db_session.add(UserProfile(
        user_id=admin_user.id, display_name="Unl", role="viewer",
        source="local", account_active=True,
    ))
    db_session.add(RequestQuota(
        user_id=admin_user.id, month="2026-06", max_allowed=10,
        mode="auto", unlimited=True, auto_min=2, auto_max=15,
    ))
    await db_session.commit()

    res = await qa.recompute_auto_quotas(db_session, now=datetime.now(timezone.utc))
    assert res == {"processed": 0, "changed": 0}

    refreshed = (await db_session.execute(
        select(RequestQuota).where(RequestQuota.user_id == admin_user.id)
    )).scalar_one()
    assert refreshed.max_allowed == 10  # unlimited rows are never recomputed


@pytest.mark.asyncio
async def test_recompute_runs_when_enabled_setting_blank(admin_user, db_session):
    from models.settings import Setting

    _seed_auto_quota(db_session, admin_user)
    # A blank value reads as ON; only an explicit false-y string disables.
    db_session.add(Setting(key="quota.auto.enabled", value=""))
    await db_session.commit()

    res = await qa.recompute_auto_quotas(db_session, now=datetime.now(timezone.utc))
    assert "skipped" not in res
    assert res["processed"] == 1


@pytest.mark.asyncio
async def test_handler_runs_engine_only_at_midnight_hour(db_session, monkeypatch):
    """The scheduler wrapper fires hourly but only runs the engine during the
    server's local-midnight hour (the hour != 0 guard)."""
    from services.scheduler import _handlers

    calls = []

    async def fake_recompute(_db, *, now=None):
        calls.append(True)
        return {"processed": 0, "changed": 0}

    monkeypatch.setattr("services.portal.quota_auto.recompute_auto_quotas", fake_recompute)

    class _Clock:
        hour = 12

        @classmethod
        def now(cls, tz=None):
            return cls

    monkeypatch.setattr(_handlers, "datetime", _Clock)
    await _handlers._handler_quota_recompute(db_session)
    assert calls == []  # not the midnight hour -> engine skipped

    _Clock.hour = 0
    await _handlers._handler_quota_recompute(db_session)
    assert calls == [True]  # midnight hour -> engine runs
