"""Portal feedback (cycle 3a): pending storage, ui gating flags, permission,
and the delegated submit endpoint."""
import pytest
from sqlalchemy import select

from api.portal.auth import _serialize_ui_flags
from api.portal.deps import _PERMISSION_COLUMNS, require_permission
from models.portal.feedback_report import FeedbackReport
from models.portal.profile import UserProfile
from services.feedback import create_pending_report, save_feedback_config

_WEBHOOK = "https://discord.com/api/webhooks/123/abcDEF"


@pytest.mark.asyncio
async def test_create_pending_report_stores_pending(db_session):
    await create_pending_report(
        db_session,
        reporter_user_id=None,
        reporter_name="Dan",
        fields={
            "type": "bug",
            "title": "Boom",
            "description": "it broke",
            "platform": "desktop",
            "tags": ["Urgent"],
            "zone": "Z",
            "module": "M",
        },
    )
    row = (await db_session.execute(select(FeedbackReport))).scalar_one()
    assert row.status == "pending"
    assert row.title == "Boom"
    assert row.reporter_name == "Dan"
    assert row.tags == ["Urgent"]
    assert row.rejected_at is None


def _profile(role="viewer", can_report=False):
    return UserProfile(user_id=1, display_name="X", role=role, can_report_feedback=can_report)


@pytest.mark.asyncio
async def test_ui_flags_gate_feedback(db_session):
    # No config -> feature off; viewer without the permission -> can_report False.
    flags = await _serialize_ui_flags(db_session, _profile())
    assert flags["feedback_enabled"] is False
    assert flags["can_report"] is False
    # Enabled + webhook configured -> feedback_enabled True.
    await save_feedback_config(db_session, enabled=True, webhook_url=_WEBHOOK)
    assert (await _serialize_ui_flags(db_session, _profile(can_report=True)))["feedback_enabled"] is True
    assert (await _serialize_ui_flags(db_session, _profile(can_report=True)))["can_report"] is True
    assert (await _serialize_ui_flags(db_session, _profile(can_report=False)))["can_report"] is False
    # Admin may always report.
    assert (await _serialize_ui_flags(db_session, _profile(role="admin")))["can_report"] is True


def test_can_report_feedback_permission_registered():
    assert "can_report_feedback" in _PERMISSION_COLUMNS
    require_permission("can_report_feedback")  # must not raise ValueError


@pytest.mark.asyncio
async def test_submit_portal_feedback_stores_pending(client, admin_user, portal_login, db_session):
    await portal_login(client)
    prof = (await db_session.execute(select(UserProfile))).scalars().first()
    assert prof is not None
    prof.can_report_feedback = True  # grant regardless of provisioned role
    await db_session.commit()
    await save_feedback_config(db_session, enabled=True, webhook_url=_WEBHOOK)

    r = await client.post(
        "/api/portal/feedback",
        json={"title": "x", "description": "y", "platform": "desktop"},
    )
    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True}
    row = (
        await db_session.execute(
            select(FeedbackReport).where(FeedbackReport.status == "pending")
        )
    ).scalars().first()
    assert row is not None and row.title == "x"


@pytest.mark.asyncio
async def test_submit_portal_feedback_requires_config(client, admin_user, portal_login, db_session):
    await portal_login(client)
    prof = (await db_session.execute(select(UserProfile))).scalars().first()
    if prof:
        prof.can_report_feedback = True
        await db_session.commit()
    r = await client.post("/api/portal/feedback", json={"title": "x", "description": "y"})
    assert r.status_code == 400
    assert r.json()["detail"] == "not_configured"


@pytest.mark.asyncio
async def test_submit_portal_feedback_denied_without_permission(client, admin_user, portal_login, db_session):
    # A non-admin portal user lacking can_report_feedback must be refused (admins
    # always bypass require_permission, so demote the role to exercise the gate).
    await portal_login(client)
    prof = (await db_session.execute(select(UserProfile))).scalars().first()
    prof.role = "viewer"
    prof.can_report_feedback = False
    await db_session.commit()
    await save_feedback_config(db_session, enabled=True, webhook_url=_WEBHOOK)
    r = await client.post("/api/portal/feedback", json={"title": "x", "description": "y"})
    assert r.status_code == 403
    assert r.json()["detail"] == "permission_denied:can_report_feedback"
