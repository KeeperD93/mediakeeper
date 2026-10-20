"""Rejecting a request, pending or already approved, puts a bell notification
with the reason in the requester's bell, and never crashes once the requester
account was purged."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from models.portal.event import MKNotification
from models.portal.request import MediaRequest
from services.portal.requests import update_request_status


async def _request(db, user_id: int | None, status: str) -> int:
    req = MediaRequest(
        user_id=user_id, tmdb_id=42, media_type="movie", title="Sample Movie", status=status,
    )
    db.add(req)
    await db.commit()
    return req.id


async def _bell(db) -> list[MKNotification]:
    return list((await db.execute(select(MKNotification))).scalars().all())


@pytest.mark.asyncio
@pytest.mark.parametrize(("status", "reason"), [("approved", "Not on any service"), ("pending", None)])
async def test_rejection_notifies_the_requester_with_the_reason(db_session, status, reason, make_user):
    uid = (await make_user("viewer")).id
    admin_id = (await make_user("admin")).id
    rid = await _request(db_session, uid, status)

    result = await update_request_status(db_session, rid, "rejected", admin_id, reason)

    assert result["success"] is True
    [notif] = await _bell(db_session)
    assert notif.user_id == uid
    assert notif.type == "request_rejected"
    assert notif.payload["request_id"] == rid
    assert notif.payload["title"] == "Sample Movie"
    assert notif.payload["reason"] == reason


@pytest.mark.asyncio
async def test_rejection_of_a_purged_requester_skips_the_bell(db_session, make_user):
    admin_id = (await make_user("admin")).id
    rid = await _request(db_session, None, "approved")

    result = await update_request_status(db_session, rid, "rejected", admin_id, "Duplicate")

    assert result["success"] is True
    assert await _bell(db_session) == []
