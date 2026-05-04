"""HTTP-level tests for the deletion-request user surface.

* ``POST /api/portal/me/deletion-request`` schedules a delayed
  deletion and stamps both timestamps on the ``users`` row.
* ``DELETE /api/portal/me/deletion-request`` clears the timestamps.

Both are gated by ``gdpr.enabled`` and answer 404 when the toggle is
off. The POST is idempotent — a second call while a request is pending
returns 409 with the existing schedule so the UI can render the
banner without a second submit.
"""
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from models.user import User
from services.settings import set_setting
from tests._portal_profile_helpers import (
    PORTAL_COOKIE,
    make_portal_user,
    portal_token,
)


async def _enable_gdpr(db_session, *, delay_days: int = 30) -> None:
    await set_setting(db_session, "gdpr.enabled", "true")
    await set_setting(db_session, "gdpr.account_purge_delay_days", str(delay_days))


async def _seed_user(client, db_session, *, username="dr"):
    user, profile = await make_portal_user(
        db_session, username=username, role="viewer"
    )
    client.cookies.set(PORTAL_COOKIE, portal_token(username))
    return user, profile


# ---------------------------------------------------------------------------
# Gating + auth
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_deletion_request_returns_404_when_gdpr_disabled(client, db_session):
    await _seed_user(client, db_session, username="dr-off")
    resp = await client.post("/api/portal/me/deletion-request")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_deletion_request_returns_404_when_gdpr_disabled(client, db_session):
    await _seed_user(client, db_session, username="dr-off-cancel")
    resp = await client.delete("/api/portal/me/deletion-request")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_deletion_request_requires_auth(client, db_session):
    await _enable_gdpr(db_session)
    resp = await client.post("/api/portal/me/deletion-request")
    # No cookie set → portal deps reject.
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_deletion_request_stamps_both_timestamps(client, db_session):
    await _enable_gdpr(db_session, delay_days=14)
    user, _ = await _seed_user(client, db_session, username="dr-on")

    resp = await client.post("/api/portal/me/deletion-request")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "pending"
    assert body["deletion_requested_at"] is not None
    assert body["pending_deletion_at"] is not None

    # The DB row was updated. Refresh through the test session because
    # the API uses its own session and our identity map is stale.
    await db_session.refresh(user)
    assert user.deletion_requested_at is not None
    assert user.pending_deletion_at is not None
    delta = user.pending_deletion_at - user.deletion_requested_at
    # Within a generous tolerance of the configured 14d delay.
    assert 13 <= delta.days <= 15


@pytest.mark.asyncio
async def test_deletion_request_does_not_force_logout(client, db_session):
    """A1 from the kickoff: a deletion request keeps the user logged
    in so they can cancel during the grace period — no
    ``tokens_invalidated_at`` bump on submit."""
    await _enable_gdpr(db_session)
    user, profile = await _seed_user(client, db_session, username="no-logout")
    before = profile.tokens_invalidated_at

    resp = await client.post("/api/portal/me/deletion-request")
    assert resp.status_code == 200

    await db_session.refresh(profile)
    assert profile.tokens_invalidated_at == before


@pytest.mark.asyncio
async def test_deletion_request_is_idempotent_409_when_already_active(client, db_session):
    await _enable_gdpr(db_session)
    await _seed_user(client, db_session, username="dr-409")

    first = await client.post("/api/portal/me/deletion-request")
    assert first.status_code == 200

    second = await client.post("/api/portal/me/deletion-request")
    assert second.status_code == 409
    detail = second.json()["detail"]
    assert detail["code"] == "already_pending"
    assert detail["pending_deletion_at"] is not None


# ---------------------------------------------------------------------------
# DELETE (cancel)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_deletion_request_clears_timestamps(client, db_session):
    await _enable_gdpr(db_session)
    user, _ = await _seed_user(client, db_session, username="cancel-ok")

    submit = await client.post("/api/portal/me/deletion-request")
    assert submit.status_code == 200

    cancel = await client.delete("/api/portal/me/deletion-request")
    assert cancel.status_code == 200
    assert cancel.json() == {"status": "cancelled"}

    await db_session.refresh(user)
    assert user.deletion_requested_at is None
    assert user.pending_deletion_at is None


@pytest.mark.asyncio
async def test_cancel_deletion_request_returns_404_when_no_pending_request(client, db_session):
    await _enable_gdpr(db_session)
    await _seed_user(client, db_session, username="cancel-empty")

    resp = await client.delete("/api/portal/me/deletion-request")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "no_pending_request"}
