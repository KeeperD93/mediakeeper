"""Admin-side tests for GDPR opt-in surfaces.

* ``GET /api/portal/admin/users?pending_deletion=true`` filters the
  list to users currently in the grace period.
* ``DELETE /api/portal/admin/users/{profile_id}/deletion-request``
  cancels the pending request from the admin side.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from core.security import create_access_token
from models.portal.audit import AdminAuditLog
from models.portal.profile import UserProfile
from models.user import User
from services.portal.admin_users_constants import (
    ACTION_USER_DELETION_REQUEST_CANCELLED,
)
from tests._portal_profile_helpers import make_portal_user


def _auth_admin(client, admin_user) -> None:
    client.cookies.set(
        "mk_token",
        create_access_token({"sub": admin_user.username, "scope": "admin"}),
    )


async def _admin_profile(db_session, admin_user) -> None:
    db_session.add(UserProfile(
        user_id=admin_user.id,
        display_name="Admin",
        role="admin",
        source="local",
        account_active=True,
    ))
    await db_session.commit()


# ---------------------------------------------------------------------------
# Pending deletion filter on the list endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_users_pending_deletion_filter_returns_only_marked_users(
    client, admin_user, db_session,
):
    await _admin_profile(db_session, admin_user)

    # Two users: one pending deletion, one not.
    pending_user, _ = await make_portal_user(
        db_session, username="pending-one", role="viewer",
    )
    pending_user.deletion_requested_at = datetime.now(timezone.utc)
    pending_user.pending_deletion_at = datetime.now(timezone.utc) + timedelta(days=14)
    db_session.add(pending_user)
    await make_portal_user(db_session, username="not-pending", role="viewer")
    await db_session.commit()

    _auth_admin(client, admin_user)
    resp = await client.get("/api/portal/admin/users?pending_deletion=true")
    assert resp.status_code == 200
    items = resp.json()["items"]
    usernames = {row["username"] for row in items}
    assert "pending-one" in usernames
    assert "not-pending" not in usernames
    assert "admin" not in usernames


@pytest.mark.asyncio
async def test_list_users_serializes_deletion_timestamps(
    client, admin_user, db_session,
):
    """Phase 11B.2 (admin DataTable) consumes these two fields — make
    sure the row payload exposes them in ISO 8601 form."""
    await _admin_profile(db_session, admin_user)
    user, _ = await make_portal_user(
        db_session, username="iso-stamps", role="viewer",
    )
    user.deletion_requested_at = datetime.now(timezone.utc)
    user.pending_deletion_at = datetime.now(timezone.utc) + timedelta(days=21)
    db_session.add(user)
    await db_session.commit()

    _auth_admin(client, admin_user)
    resp = await client.get("/api/portal/admin/users?pending_deletion=true")
    assert resp.status_code == 200
    [row] = resp.json()["items"]
    assert row["deletion_requested_at"] is not None
    assert row["pending_deletion_at"] is not None


# ---------------------------------------------------------------------------
# Admin cancel
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_cancel_deletion_request_clears_user_timestamps(
    client, admin_user, db_session,
):
    await _admin_profile(db_session, admin_user)
    user, profile = await make_portal_user(
        db_session, username="admin-cancel", role="viewer",
    )
    user.deletion_requested_at = datetime.now(timezone.utc)
    user.pending_deletion_at = datetime.now(timezone.utc) + timedelta(days=14)
    db_session.add(user)
    await db_session.commit()

    _auth_admin(client, admin_user)
    resp = await client.delete(
        f"/api/portal/admin/users/{profile.id}/deletion-request"
    )
    assert resp.status_code == 200, resp.text

    await db_session.refresh(user)
    assert user.deletion_requested_at is None
    assert user.pending_deletion_at is None


@pytest.mark.asyncio
async def test_admin_cancel_does_not_touch_tokens_invalidated_at(
    client, admin_user, db_session,
):
    """A7 from the kickoff: admin cancel only resets timestamps, never
    bumps ``tokens_invalidated_at``."""
    await _admin_profile(db_session, admin_user)
    user, profile = await make_portal_user(
        db_session, username="no-token-bump", role="viewer",
    )
    user.deletion_requested_at = datetime.now(timezone.utc)
    user.pending_deletion_at = datetime.now(timezone.utc) + timedelta(days=14)
    db_session.add(user)
    await db_session.commit()
    before = profile.tokens_invalidated_at

    _auth_admin(client, admin_user)
    resp = await client.delete(
        f"/api/portal/admin/users/{profile.id}/deletion-request"
    )
    assert resp.status_code == 200

    await db_session.refresh(profile)
    assert profile.tokens_invalidated_at == before


@pytest.mark.asyncio
async def test_admin_cancel_writes_audit_row(
    client, admin_user, db_session,
):
    await _admin_profile(db_session, admin_user)
    user, profile = await make_portal_user(
        db_session, username="audit-row", role="viewer",
    )
    user.deletion_requested_at = datetime.now(timezone.utc)
    user.pending_deletion_at = datetime.now(timezone.utc) + timedelta(days=14)
    db_session.add(user)
    await db_session.commit()

    _auth_admin(client, admin_user)
    resp = await client.delete(
        f"/api/portal/admin/users/{profile.id}/deletion-request"
    )
    assert resp.status_code == 200

    audit = (await db_session.execute(
        select(AdminAuditLog).where(
            AdminAuditLog.action == ACTION_USER_DELETION_REQUEST_CANCELLED,
            AdminAuditLog.target_user_id == user.id,
        )
    )).scalar_one_or_none()
    assert audit is not None


@pytest.mark.asyncio
async def test_admin_cancel_returns_404_when_no_pending_request(
    client, admin_user, db_session,
):
    await _admin_profile(db_session, admin_user)
    _, profile = await make_portal_user(
        db_session, username="nothing-pending", role="viewer",
    )

    _auth_admin(client, admin_user)
    resp = await client.delete(
        f"/api/portal/admin/users/{profile.id}/deletion-request"
    )
    assert resp.status_code == 404
    assert resp.json() == {"detail": "no_pending_request"}
