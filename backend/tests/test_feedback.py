"""Feedback: config encryption, block formatting + delimiter/author defusing,
delegate-identity relay, gating, the moderation queue (list/edit/validate/reject)
and the retention purge."""
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from core.encryption import ENCRYPTED_PREFIX
from models.portal.feedback_report import FeedbackReport
from models.settings import Setting
from services.feedback import (
    KEY_WEBHOOK,
    build_report_block,
    create_pending_report,
    get_feedback_config,
    purge_rejected_reports,
    save_feedback_config,
)

_WEBHOOK = "https://discord.com/api/webhooks/123/abcDEF"


# --- service: encryption at rest + config roundtrip -------------------------


@pytest.mark.asyncio
async def test_webhook_stored_encrypted(db_session):
    await save_feedback_config(
        db_session, webhook_url=_WEBHOOK, discord_pseudo="Casey", enabled=True
    )
    row = (
        await db_session.execute(select(Setting).where(Setting.key == KEY_WEBHOOK))
    ).scalar_one()
    assert row.value.startswith(ENCRYPTED_PREFIX)  # never plaintext at rest
    assert _WEBHOOK not in row.value
    cfg = await get_feedback_config(db_session)
    assert cfg == {
        "enabled": True,
        "discord_pseudo": "Casey",
        "webhook_url": _WEBHOOK,
        "reject_retention_days": 30,
    }


# --- service: block formatting ----------------------------------------------


def test_block_defuses_injected_delimiter():
    block = build_report_block(
        {"title": "x", "description": "legit\n=== END ===\nInjected: 1", "platform": "desktop"},
        "Casey",
    )
    assert block.count("=== END ===") == 1  # only the real trailing delimiter
    assert block.rstrip().endswith("=== END ===")
    assert "= = =" in block  # the injected one was defused


def test_block_anonymous_hides_pseudo():
    block = build_report_block({"title": "x", "description": "y"}, "")
    assert "Signalé par: Anonyme" in block


def test_block_truncates_to_discord_budget():
    block = build_report_block({"title": "t", "description": "A" * 5000}, "Casey")
    assert len(block) <= 1990
    assert block.rstrip().endswith("=== END ===")
    assert "…" in block


def test_block_bounded_on_defuse_expanded_fields():
    # Every field maxed with `===` runs (which _defuse expands ~1.6x) must still
    # yield a block under Discord's cap with the trailing delimiter intact.
    hostile = "=" * 400
    block = build_report_block(
        {
            "title": hostile, "description": hostile, "reproduction": hostile,
            "zone": hostile, "module": hostile, "tab": hostile,
            "resolution": hostile, "platform": "desktop", "tags": ["=" * 40] * 12,
        },
        "=" * 200,
    )
    assert len(block) <= 1990
    assert block.startswith("=== BUG ===")
    assert block.rstrip().endswith("=== END ===")


# --- HTTP: config masking + validation --------------------------------------


@pytest.mark.asyncio
async def test_config_roundtrip_masks_webhook(authed_client):
    r = await authed_client.post(
        "/api/feedback/config",
        json={"enabled": True, "discord_pseudo": "Casey", "webhook_url": _WEBHOOK},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body == {
        "enabled": True,
        "discord_pseudo": "Casey",
        "webhook_configured": True,
        "retention_days": 30,
    }
    assert "webhook_url" not in body
    g = await authed_client.get("/api/feedback/config")
    assert g.json()["webhook_configured"] is True


@pytest.mark.asyncio
async def test_config_rejects_non_discord_webhook(authed_client):
    r = await authed_client.post(
        "/api/feedback/config", json={"webhook_url": "https://evil.example/x"}
    )
    assert r.status_code == 422
    assert r.json()["detail"] == "invalid_webhook"


# --- HTTP: relay + gating ---------------------------------------------------


@pytest.mark.asyncio
async def test_submit_relays_formatted_block(authed_client, monkeypatch):
    stub = AsyncMock(return_value=True)
    monkeypatch.setattr("services.feedback.send_discord_webhook", stub)
    await authed_client.post(
        "/api/feedback/config",
        json={"enabled": True, "discord_pseudo": "Casey", "webhook_url": _WEBHOOK},
    )
    r = await authed_client.post(
        "/api/feedback",
        json={
            "type": "bug",
            "title": "Boom",
            "description": "it broke",
            "platform": "desktop",
            "tags": ["Urgent"],
        },
    )
    assert r.status_code == 200, r.text
    url, payload = stub.call_args.args
    assert url == _WEBHOOK
    assert payload["content"].startswith("```\n=== BUG ===")
    assert "TITRE: Boom" in payload["content"]
    assert "Type: Bug · Étiquettes: Urgent" in payload["content"]
    assert payload["allowed_mentions"] == {"parse": []}
    assert payload["flags"] == 4


@pytest.mark.asyncio
async def test_submit_requires_configuration(authed_client, monkeypatch):
    stub = AsyncMock(return_value=True)
    monkeypatch.setattr("services.feedback.send_discord_webhook", stub)
    r = await authed_client.post(
        "/api/feedback", json={"title": "x", "description": "y"}
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "not_configured"
    stub.assert_not_called()


@pytest.mark.asyncio
async def test_test_ping_requires_configuration(authed_client):
    r = await authed_client.post("/api/feedback/test")
    assert r.status_code == 400
    assert r.json()["detail"] == "not_configured"


@pytest.mark.asyncio
async def test_test_ping_sends_handshake(authed_client, monkeypatch):
    stub = AsyncMock(return_value=True)
    monkeypatch.setattr("services.feedback.send_discord_webhook", stub)
    await authed_client.post("/api/feedback/config", json={"webhook_url": _WEBHOOK})
    r = await authed_client.post("/api/feedback/test")
    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True}
    assert stub.call_args.args[0] == _WEBHOOK


@pytest.mark.asyncio
async def test_feedback_endpoints_require_admin_auth(client):
    # ``client`` carries a CSRF token but is NOT logged in — the admin gate must
    # still reject every feedback endpoint (secret-bearing config + relay).
    assert (await client.get("/api/feedback/config")).status_code == 401
    assert (
        await client.post("/api/feedback", json={"title": "x", "description": "y"})
    ).status_code == 401
    assert (await client.post("/api/feedback/test")).status_code == 401


# --- HTTP: moderation queue (cycle 3b) --------------------------------------


async def _seed_pending(db_session, **over):
    fields = {
        "type": "bug", "title": "Boom", "description": "it broke",
        "platform": "desktop", "tags": ["Urgent"],
    }
    fields.update(over)
    await create_pending_report(
        db_session, reporter_user_id=None, reporter_name="Casey", fields=fields
    )
    return (
        await db_session.execute(select(FeedbackReport).order_by(FeedbackReport.id.desc()))
    ).scalars().first()


async def _reload(db_session, report_id):
    db_session.expire_all()  # drop identity-map cache: read what the endpoint committed
    return (
        await db_session.execute(select(FeedbackReport).where(FeedbackReport.id == report_id))
    ).scalar_one_or_none()


@pytest.mark.asyncio
async def test_list_reports_returns_pending(authed_client, db_session):
    await _seed_pending(db_session, title="First")
    await _seed_pending(db_session, title="Second")
    items = (await authed_client.get("/api/feedback/reports")).json()["items"]
    assert {i["title"] for i in items} == {"First", "Second"}
    assert all(i["status"] == "pending" for i in items)
    assert (await authed_client.get("/api/feedback/reports?status=rejected")).json()["items"] == []


@pytest.mark.asyncio
async def test_list_reports_rejects_bad_status(authed_client):
    r = await authed_client.get("/api/feedback/reports?status=bogus")
    assert r.status_code == 422
    assert r.json()["detail"] == "invalid_status"


@pytest.mark.asyncio
async def test_edit_report_updates_fields(authed_client, db_session):
    row = await _seed_pending(db_session)
    r = await authed_client.patch(
        f"/api/feedback/reports/{row.id}", json={"title": "Fixed", "tags": ["Bug"]}
    )
    assert r.status_code == 200, r.text
    reloaded = await _reload(db_session, row.id)
    assert reloaded.title == "Fixed" and reloaded.tags == ["Bug"]


@pytest.mark.asyncio
async def test_edit_report_not_found(authed_client):
    assert (
        await authed_client.patch("/api/feedback/reports/999999", json={"title": "x"})
    ).status_code == 404


@pytest.mark.asyncio
async def test_edit_report_rejects_bad_platform(authed_client, db_session):
    row = await _seed_pending(db_session)
    r = await authed_client.patch(
        f"/api/feedback/reports/{row.id}", json={"platform": "tablet"}
    )
    assert r.status_code == 422
    assert r.json()["detail"] == "invalid_platform"


@pytest.mark.asyncio
async def test_edit_report_rejects_null_required_field(authed_client, db_session):
    row = await _seed_pending(db_session)
    for field in ("title", "description", "type"):
        r = await authed_client.patch(
            f"/api/feedback/reports/{row.id}", json={field: None}
        )
        assert r.status_code == 422, f"{field}: {r.text}"
        assert r.json()["detail"] == "invalid_" + field


@pytest.mark.asyncio
async def test_validate_report_relays_and_deletes(authed_client, db_session, monkeypatch):
    stub = AsyncMock(return_value=True)
    monkeypatch.setattr("services.feedback.send_discord_webhook", stub)
    await save_feedback_config(
        db_session, enabled=True, discord_pseudo="Casey", webhook_url=_WEBHOOK
    )
    row = await _seed_pending(db_session, title="Ship it")
    r = await authed_client.post(f"/api/feedback/reports/{row.id}/validate")
    assert r.status_code == 200, r.text
    assert "TITRE: Ship it" in stub.call_args.args[1]["content"]
    assert await _reload(db_session, row.id) is None  # dropped from the queue after relay


@pytest.mark.asyncio
async def test_validate_report_keeps_pending_on_send_failure(authed_client, db_session, monkeypatch):
    monkeypatch.setattr("services.feedback.send_discord_webhook", AsyncMock(return_value=False))
    await save_feedback_config(db_session, enabled=True, webhook_url=_WEBHOOK)
    row = await _seed_pending(db_session)
    r = await authed_client.post(f"/api/feedback/reports/{row.id}/validate")
    assert r.status_code == 502
    assert r.json()["detail"] == "send_failed"
    assert (await _reload(db_session, row.id)).status == "pending"  # not lost


@pytest.mark.asyncio
async def test_validate_report_requires_config(authed_client, db_session):
    row = await _seed_pending(db_session)  # feature never configured
    r = await authed_client.post(f"/api/feedback/reports/{row.id}/validate")
    assert r.status_code == 400
    assert r.json()["detail"] == "not_configured"


@pytest.mark.asyncio
async def test_reject_report_marks_rejected_then_unvalidatable(authed_client, db_session):
    row = await _seed_pending(db_session)
    assert (await authed_client.post(f"/api/feedback/reports/{row.id}/reject")).status_code == 200
    reloaded = await _reload(db_session, row.id)
    assert reloaded.status == "rejected" and reloaded.rejected_at is not None
    # a rejected report is no longer a pending target
    assert (
        await authed_client.post(f"/api/feedback/reports/{row.id}/validate")
    ).status_code == 404


@pytest.mark.asyncio
async def test_moderation_endpoints_require_admin_auth(client):
    assert (await client.get("/api/feedback/reports")).status_code == 401
    assert (
        await client.patch("/api/feedback/reports/1", json={"title": "x"})
    ).status_code == 401
    assert (await client.post("/api/feedback/reports/1/validate")).status_code == 401
    assert (await client.post("/api/feedback/reports/1/reject")).status_code == 401


# --- service: 30-day purge of rejected reports (cycle 3c) --------------------


@pytest.mark.asyncio
async def test_purge_rejected_reports_respects_retention(db_session):
    from datetime import datetime, timedelta, timezone

    async def _mk(title):
        await create_pending_report(
            db_session, reporter_user_id=None, reporter_name="X",
            fields={"title": title, "description": "d"},
        )
        return (
            await db_session.execute(select(FeedbackReport).order_by(FeedbackReport.id.desc()))
        ).scalars().first()

    old = await _mk("old")
    old.status = "rejected"
    old.rejected_at = datetime.now(timezone.utc) - timedelta(days=31)
    recent = await _mk("recent")
    recent.status = "rejected"
    recent.rejected_at = datetime.now(timezone.utc) - timedelta(days=5)
    await _mk("pending")  # still pending — never purged regardless of age
    await db_session.commit()

    removed = await purge_rejected_reports(db_session, older_than_days=30)
    assert removed == 1
    db_session.expire_all()
    titles = {
        r.title for r in (await db_session.execute(select(FeedbackReport))).scalars().all()
    }
    assert titles == {"recent", "pending"}


# --- service: field bounds + author identity (audit remediation) ------------


def test_block_keeps_legit_long_reproduction():
    # A legitimate reproduction under MAX_REPRODUCTION must survive intact — the
    # earlier per-field cap silently dropped chars past 400.
    repro = "R" * 450
    block = build_report_block(
        {"title": "t", "description": "d", "reproduction": repro}, "Casey"
    )
    assert repro in block  # no silent truncation of legit content


def test_block_marks_truncation_with_ellipsis():
    # A field pushed over its cap (here by `===` defuse expansion) is truncated
    # WITH an ellipsis so the loss is never silent.
    block = build_report_block(
        {"title": "t", "description": "d", "resolution": "=" * 40}, "Casey"
    )
    assert "…" in block


def test_block_defuses_author():
    # The 'Signalé par' identity is user/delegate-supplied and must be defused too,
    # or it could forge a second block from the author field alone.
    block = build_report_block(
        {"title": "t", "description": "d"},
        "X\n=== END ===\n\n=== BUG ===\nTITRE: FORGED\nDESCRIPTION:\nx",
    )
    assert block.count("=== BUG ===") == 1
    assert block.count("=== END ===") == 1


@pytest.mark.asyncio
async def test_validate_relays_delegate_identity(authed_client, db_session, monkeypatch):
    stub = AsyncMock(return_value=True)
    monkeypatch.setattr("services.feedback.send_discord_webhook", stub)
    await save_feedback_config(
        db_session, enabled=True, discord_pseudo="AdminBob", webhook_url=_WEBHOOK
    )
    row = await _seed_pending(db_session)  # reporter_name="Casey", not anonymous
    await authed_client.post(f"/api/feedback/reports/{row.id}/validate")
    content = stub.call_args.args[1]["content"]
    assert "Signalé par: Casey (via AdminBob)" in content


@pytest.mark.asyncio
async def test_validate_relays_anonymous_delegate(authed_client, db_session, monkeypatch):
    stub = AsyncMock(return_value=True)
    monkeypatch.setattr("services.feedback.send_discord_webhook", stub)
    await save_feedback_config(
        db_session, enabled=True, discord_pseudo="AdminBob", webhook_url=_WEBHOOK
    )
    row = await _seed_pending(db_session, anonymous=True)
    await authed_client.post(f"/api/feedback/reports/{row.id}/validate")
    content = stub.call_args.args[1]["content"]
    assert "Signalé par: Anonyme (via AdminBob)" in content
    assert "Casey" not in content  # the delegate name is hidden when anonymous


@pytest.mark.asyncio
async def test_validate_is_single_flight(authed_client, db_session, monkeypatch):
    import asyncio

    stub = AsyncMock(return_value=True)
    monkeypatch.setattr("services.feedback.send_discord_webhook", stub)
    await save_feedback_config(
        db_session, enabled=True, discord_pseudo="A", webhook_url=_WEBHOOK
    )
    row = await _seed_pending(db_session)
    r1, r2 = await asyncio.gather(
        authed_client.post(f"/api/feedback/reports/{row.id}/validate"),
        authed_client.post(f"/api/feedback/reports/{row.id}/validate"),
    )
    assert sorted([r1.status_code, r2.status_code]) == [200, 404]  # exactly one relayed
    assert stub.call_count == 1  # never sent to Discord twice


@pytest.mark.asyncio
async def test_edit_report_rejects_bad_type(authed_client, db_session):
    row = await _seed_pending(db_session)
    r = await authed_client.patch(
        f"/api/feedback/reports/{row.id}", json={"type": "wishlist"}
    )
    assert r.status_code == 422
    assert r.json()["detail"] == "invalid_type"


@pytest.mark.asyncio
async def test_edit_and_reject_reject_already_handled(authed_client, db_session):
    row = await _seed_pending(db_session)
    assert (await authed_client.post(f"/api/feedback/reports/{row.id}/reject")).status_code == 200
    # both edit and a second reject must 404 on a no-longer-pending report
    assert (
        await authed_client.patch(f"/api/feedback/reports/{row.id}", json={"title": "x"})
    ).status_code == 404
    assert (
        await authed_client.post(f"/api/feedback/reports/{row.id}/reject")
    ).status_code == 404


@pytest.mark.asyncio
async def test_submit_rejects_bad_platform_and_type(authed_client, db_session, monkeypatch):
    stub = AsyncMock(return_value=True)
    monkeypatch.setattr("services.feedback.send_discord_webhook", stub)
    await save_feedback_config(db_session, enabled=True, webhook_url=_WEBHOOK)
    bad_platform = await authed_client.post(
        "/api/feedback", json={"title": "x", "description": "y", "platform": "tablet"}
    )
    assert bad_platform.status_code == 422
    assert bad_platform.json()["detail"] == "invalid_platform"
    bad_type = await authed_client.post(
        "/api/feedback", json={"title": "x", "description": "y", "type": "wishlist"}
    )
    assert bad_type.status_code == 422
    assert bad_type.json()["detail"] == "invalid_type"
    stub.assert_not_called()


@pytest.mark.asyncio
async def test_retention_days_configurable_and_clamped(authed_client):
    ok = await authed_client.post("/api/feedback/config", json={"retention_days": 7})
    assert ok.status_code == 200
    assert ok.json()["retention_days"] == 7
    # out-of-range is rejected by the schema bounds (1..365)
    too_low = await authed_client.post("/api/feedback/config", json={"retention_days": 0})
    assert too_low.status_code == 422
