"""End-to-end HTTP workflow tests for the requests module.

Covers the slice that was audit-flagged as ""zero HTTP coverage":
- PUT /requests/{id}/status → approve / reject transitions
- POST /requests → quota decrement path
- GET /requests/quota → snapshot
"""
import pytest
from sqlalchemy import select

from core.security import create_access_token, hash_password
from models.portal.profile import UserProfile
from models.portal.request import MediaRequest, RequestQuota
from models.user import User


async def _bootstrap(db, username, role="viewer"):
    user = User(
        username=username,
        hashed_password=hash_password("Irrelevant123!"),
        is_active=True,
        must_change_password=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    profile = UserProfile(
        user_id=user.id,
        display_name=username,
        role=role,
        account_active=True,
    )
    db.add(profile)
    await db.commit()
    return user, profile


def _rq(client, user):
    client.cookies.set(
        "rq_token",
        create_access_token({"sub": user.username, "scope": "portal"}),
    )


@pytest.mark.asyncio
async def test_admin_can_approve_then_status_is_persisted(client, db_session):
    user, _ = await _bootstrap(db_session, "viewer1")
    admin, _ = await _bootstrap(db_session, "admin_dm", role="admin")

    req = MediaRequest(
        user_id=user.id,
        tmdb_id=101,
        media_type="movie",
        title="Demo",
        status="pending",
    )
    db_session.add(req)
    await db_session.commit()
    await db_session.refresh(req)

    _rq(client, admin)
    resp = await client.put(
        f"/api/portal/requests/{req.id}/status",
        json={"status": "approved"},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # The endpoint wrote via its own session override; expire the local one
    # so the next read picks up the committed row.
    await db_session.commit()  # release any pending txn before re-read
    refreshed = (
        await db_session.execute(
            select(MediaRequest).where(MediaRequest.id == req.id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    assert refreshed.status == "approved"
    assert refreshed.approved_by == admin.id


@pytest.mark.asyncio
async def test_non_admin_cannot_change_status(client, db_session):
    user, _ = await _bootstrap(db_session, "viewer2")
    other, _ = await _bootstrap(db_session, "viewer3")

    req = MediaRequest(
        user_id=user.id,
        tmdb_id=102,
        media_type="movie",
        title="Demo2",
        status="pending",
    )
    db_session.add(req)
    await db_session.commit()
    await db_session.refresh(req)

    _rq(client, other)
    resp = await client.put(
        f"/api/portal/requests/{req.id}/status",
        json={"status": "approved"},
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_reject_transition_allows_requester_to_retry(client, db_session):
    user, _ = await _bootstrap(db_session, "viewer4")
    admin, _ = await _bootstrap(db_session, "admin_dm2", role="admin")

    req = MediaRequest(
        user_id=user.id,
        tmdb_id=103,
        media_type="movie",
        title="Demo3",
        status="pending",
    )
    db_session.add(req)
    await db_session.commit()
    await db_session.refresh(req)

    _rq(client, admin)
    resp = await client.put(
        f"/api/portal/requests/{req.id}/status",
        json={"status": "rejected", "reason": "not_suitable"},
    )
    assert resp.status_code == 200

    await db_session.commit()  # release any pending txn before re-read
    refreshed = (
        await db_session.execute(
            select(MediaRequest).where(MediaRequest.id == req.id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    assert refreshed.status == "rejected"
    assert refreshed.reject_reason == "not_suitable"


@pytest.mark.asyncio
async def test_quota_snapshot_unlimited_for_admin(client, db_session):
    _, _ = await _bootstrap(db_session, "regular", role="viewer")
    admin, _ = await _bootstrap(db_session, "admin_dm3", role="admin")

    _rq(client, admin)
    resp = await client.get("/api/portal/requests/quota")
    assert resp.status_code == 200
    assert resp.json()["unlimited"] is True


@pytest.mark.asyncio
async def test_rejected_resubmit_reuses_row_and_bumps_retry_count(client, db_session):
    """POST /requests on a previously-rejected item of the same user reuses
    the existing row: status flips back to pending, reject_reason clears,
    and retry_count increments instead of creating a second row."""
    user, _ = await _bootstrap(db_session, "retryer", role="viewer")

    rejected = MediaRequest(
        user_id=user.id,
        tmdb_id=555,
        media_type="movie",
        title="Refused Movie",
        status="rejected",
        reject_reason="not_suitable",
        retry_count=0,
    )
    db_session.add(rejected)
    quota = RequestQuota(
        user_id=user.id,
        month="2026-04",
        used=0,
        max_allowed=5,
        unlimited=False,
        auto_approve=False,
    )
    db_session.add(quota)
    await db_session.commit()
    await db_session.refresh(rejected)
    original_id = rejected.id

    _rq(client, user)
    resp = await client.post(
        "/api/portal/requests",
        json={
            "tmdb_id": 555,
            "media_type": "movie",
            "title": "Refused Movie",
            "poster_url": "",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["id"] == original_id
    assert body["retry_count"] == 1

    await db_session.commit()
    rows = (
        await db_session.execute(
            select(MediaRequest).where(
                MediaRequest.user_id == user.id,
                MediaRequest.tmdb_id == 555,
            ).execution_options(populate_existing=True)
        )
    ).scalars().all()
    assert len(rows) == 1, "resubmission must not create a second row"
    row = rows[0]
    assert row.id == original_id
    assert row.status == "pending"
    assert row.reject_reason is None
    assert row.retry_count == 1


@pytest.mark.asyncio
async def test_quota_snapshot_respects_viewer_limit(client, db_session):
    user, _ = await _bootstrap(db_session, "regular2", role="viewer")
    # ``unlimited=False`` set explicitly — SQLite's string-based server_default
    # for Boolean ("false") deserializes to True, which only affects the test
    # harness. Prod (Postgres) doesn't have that quirk.
    quota = RequestQuota(
        user_id=user.id,
        month="2026-04",
        used=3,
        max_allowed=5,
        unlimited=False,
        auto_approve=False,
    )
    db_session.add(quota)
    await db_session.commit()

    _rq(client, user)
    resp = await client.get("/api/portal/requests/quota")
    assert resp.status_code == 200
    data = resp.json()
    assert data["max_allowed"] == 5
    assert data["unlimited"] is False
