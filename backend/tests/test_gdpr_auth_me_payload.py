"""``GET /api/portal/auth/me`` exposes a ``gdpr`` block (Batch 11B).

The frontend uses the block to:

* show or hide the Privacy tab in ``/portal/settings`` based on
  ``gdpr.enabled``,
* render the grace-period banner when ``pending_deletion_at`` is set.
"""
from datetime import datetime, timedelta, timezone

import pytest

from services.settings import set_setting
from tests._portal_profile_helpers import (
    PORTAL_COOKIE,
    make_portal_user,
    portal_token,
)


async def _seed(client, db_session, *, username="me-payload"):
    user, profile = await make_portal_user(
        db_session, username=username, role="viewer"
    )
    client.cookies.set(PORTAL_COOKIE, portal_token(username))
    return user, profile


@pytest.mark.asyncio
async def test_auth_me_exposes_gdpr_block_with_disabling_defaults(client, db_session):
    await _seed(client, db_session, username="me-defaults")

    resp = await client.get("/api/portal/auth/me")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "gdpr" in body
    assert body["gdpr"]["enabled"] is False
    assert body["gdpr"]["pending_deletion_at"] is None
    assert body["gdpr"]["deletion_requested_at"] is None


@pytest.mark.asyncio
async def test_auth_me_reflects_enabled_toggle(client, db_session):
    await set_setting(db_session, "gdpr.enabled", "true")
    await _seed(client, db_session, username="me-toggled")

    resp = await client.get("/api/portal/auth/me")
    assert resp.status_code == 200
    assert resp.json()["gdpr"]["enabled"] is True


@pytest.mark.asyncio
async def test_auth_me_surfaces_pending_deletion_timestamps(client, db_session):
    await set_setting(db_session, "gdpr.enabled", "true")
    user, _ = await _seed(client, db_session, username="me-pending")
    user.deletion_requested_at = datetime.now(timezone.utc)
    user.pending_deletion_at = datetime.now(timezone.utc) + timedelta(days=14)
    db_session.add(user)
    await db_session.commit()

    resp = await client.get("/api/portal/auth/me")
    assert resp.status_code == 200
    block = resp.json()["gdpr"]
    assert block["enabled"] is True
    assert block["deletion_requested_at"] is not None
    assert block["pending_deletion_at"] is not None
