"""Portal feedback: pending storage, ui gating flags, permission, and the submit
endpoint — queued for delegates, relayed straight to Discord for accounts with
back-office access."""
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select

from api.portal.auth import _serialize_ui_flags
from api.portal.deps import require_permission
from core.security import EXTERNAL_AUTH_PASSWORD_SENTINEL, create_access_token, hash_password
from models.portal.feedback_report import FeedbackReport
from models.portal.profile import UserProfile
from models.user import User
from services.feedback import create_pending_report, save_feedback_config
from services.portal.admin_users_constants import PERMISSION_KEYS

_WEBHOOK = "https://discord.com/api/webhooks/123/abcDEF"
_REPORT = {"title": "x", "description": "y", "platform": "desktop"}


@pytest.fixture
def relay(monkeypatch):
    """The Discord send, mocked (successful unless a test says otherwise)."""
    stub = AsyncMock(return_value=True)
    monkeypatch.setattr("services.feedback.send_discord_webhook", stub)
    return stub


async def _sign_in_reporter(client, db_session, user):
    """Let ``user`` report from the portal: grant the permission, set its cookie."""
    profile = (
        await db_session.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    ).scalar_one()
    profile.can_report_feedback = True
    await db_session.commit()
    client.cookies.set("rq_token", create_access_token({"sub": user.username, "scope": "portal"}))


async def _queued_count(db_session):
    return (await db_session.execute(select(func.count()).select_from(FeedbackReport))).scalar_one()


@pytest.mark.asyncio
async def test_create_pending_report_stores_pending(db_session):
    await create_pending_report(
        db_session,
        reporter_user_id=None,
        reporter_name="Casey",
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
    assert row.reporter_name == "Casey"
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
    assert "can_report_feedback" in PERMISSION_KEYS
    require_permission("can_report_feedback")  # must not raise ValueError


@pytest.mark.asyncio
async def test_delegate_report_is_queued(client, db_session, make_user, relay):
    await save_feedback_config(db_session, enabled=True, webhook_url=_WEBHOOK)
    await _sign_in_reporter(client, db_session, await make_user("delegate", role="viewer"))

    r = await client.post("/api/portal/feedback", json=_REPORT)
    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True}
    row = (await db_session.execute(select(FeedbackReport))).scalar_one()
    assert (row.status, row.title, row.reporter_name) == ("pending", "x", "delegate")
    relay.assert_not_awaited()


@pytest.mark.asyncio
async def test_portal_admin_role_without_backoffice_is_queued(
    client, db_session, make_user, relay, monkeypatch
):
    monkeypatch.setenv("MK_ADMIN_USERS", "admin")
    await save_feedback_config(db_session, enabled=True, webhook_url=_WEBHOOK)
    await _sign_in_reporter(client, db_session, await make_user("portal.admin", role="admin"))

    r = await client.post("/api/portal/feedback", json=_REPORT)
    assert r.status_code == 200, r.text
    assert await _queued_count(db_session) == 1
    relay.assert_not_awaited()


@pytest.mark.asyncio
async def test_emby_only_account_listed_as_admin_is_queued(client, db_session, relay, monkeypatch):
    # Listed in MK_ADMIN_USERS but holding only the Emby sentinel password:
    # no back-office session possible, so the report goes through moderation.
    monkeypatch.setenv("MK_ADMIN_USERS", "admin,emby.admin")
    await save_feedback_config(db_session, enabled=True, webhook_url=_WEBHOOK)
    user = User(
        username="emby.admin",
        hashed_password=hash_password(EXTERNAL_AUTH_PASSWORD_SENTINEL),
        is_active=True,
        must_change_password=False,
    )
    db_session.add(user)
    await db_session.commit()
    db_session.add(UserProfile(user_id=user.id, display_name="emby.admin", role="viewer", account_active=True))
    await db_session.commit()
    await _sign_in_reporter(client, db_session, user)

    r = await client.post("/api/portal/feedback", json=_REPORT)
    assert r.status_code == 200, r.text
    assert await _queued_count(db_session) == 1
    relay.assert_not_awaited()


@pytest.mark.asyncio
async def test_backoffice_admin_report_is_relayed_not_queued(
    client, admin_user, portal_login, db_session, relay, monkeypatch
):
    monkeypatch.setenv("MK_ADMIN_USERS", "admin")
    await save_feedback_config(
        db_session, enabled=True, webhook_url=_WEBHOOK, discord_pseudo="Maintainer"
    )
    await portal_login(client)

    r = await client.post("/api/portal/feedback", json=_REPORT)
    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True}
    relay.assert_awaited_once()
    url, payload = relay.call_args.args
    assert url == _WEBHOOK
    assert "TITRE: x" in payload["content"]
    # The admin's own report: their pseudo alone, no "(via …)".
    assert "Signalé par: Maintainer ·" in payload["content"]
    assert await _queued_count(db_session) == 0


@pytest.mark.asyncio
async def test_backoffice_admin_failed_relay_is_reported_not_queued(
    client, admin_user, portal_login, db_session, relay, monkeypatch
):
    monkeypatch.setenv("MK_ADMIN_USERS", "admin")
    relay.return_value = False
    await save_feedback_config(db_session, enabled=True, webhook_url=_WEBHOOK)
    await portal_login(client)

    r = await client.post("/api/portal/feedback", json=_REPORT)
    assert r.status_code == 502
    assert r.json()["detail"] == "send_failed"
    assert await _queued_count(db_session) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("bad_field", "detail"),
    [({"platform": "tablet"}, "invalid_platform"), ({"type": "praise"}, "invalid_type")],
)
@pytest.mark.parametrize("backoffice", [True, False], ids=["backoffice", "delegate"])
async def test_invalid_report_is_refused_before_relay_or_queue(
    client, admin_user, portal_login, db_session, make_user, relay, monkeypatch, bad_field, detail, backoffice
):
    monkeypatch.setenv("MK_ADMIN_USERS", "admin")
    await save_feedback_config(db_session, enabled=True, webhook_url=_WEBHOOK)
    if backoffice:
        await portal_login(client)
    else:
        await _sign_in_reporter(client, db_session, await make_user("delegate", role="viewer"))

    r = await client.post("/api/portal/feedback", json={**_REPORT, **bad_field})
    assert r.status_code == 422
    assert r.json()["detail"] == detail
    relay.assert_not_awaited()
    assert await _queued_count(db_session) == 0


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
