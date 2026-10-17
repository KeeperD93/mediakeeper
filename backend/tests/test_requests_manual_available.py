"""Marking a request available by hand checks Emby first, with the rules of the
automatic flip: a missing title is refused until the admin forces it, and a
wrong availability can be undone without notifying the requester again. A
stale queue resending the current status changes nothing."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from core.security import create_access_token, hash_password
from models.portal.emby_tmdb_index import EmbyTmdbIndex
from models.portal.event import MKNotification
from models.portal.profile import UserProfile
from models.portal.request import MediaRequest
from models.user import User
from services.portal import requests_fulfill
from services.portal.requests import update_request_status

TMDB_ID = 42


async def _user(db, username: str, role: str = "viewer") -> int:
    user = User(
        username=username,
        hashed_password=hash_password("Irrelevant123!"),
        is_active=True,
        must_change_password=False,
    )
    db.add(user)
    await db.commit()
    db.add(UserProfile(user_id=user.id, display_name=username, role=role, account_active=True))
    await db.commit()
    return user.id


async def _request(db, user_id: int, status: str, media_type: str = "movie", **extra) -> int:
    req = MediaRequest(
        user_id=user_id, tmdb_id=TMDB_ID, media_type=media_type, title="Sample",
        status=status, **extra,
    )
    db.add(req)
    await db.commit()
    return req.id


async def _in_emby(db, media_type: str = "movie") -> None:
    db.add(EmbyTmdbIndex(emby_item_id="EMBY-1", tmdb_id=TMDB_ID, media_type=media_type))
    await db.commit()


async def _state(db, rid: int):
    return (await db.execute(
        select(MediaRequest.status, MediaRequest.available_at, MediaRequest.approved_by)
        .where(MediaRequest.id == rid)
    )).one()


async def _row(db, rid: int):
    return (await db.execute(
        select(
            MediaRequest.status, MediaRequest.available_at, MediaRequest.approved_by,
            MediaRequest.reject_reason, MediaRequest.updated_at, MediaRequest.archived_at,
        ).where(MediaRequest.id == rid)
    )).one()


async def _bell_types(db) -> list[str]:
    return list((await db.execute(select(MKNotification.type))).scalars().all())


@pytest.mark.asyncio
async def test_missing_title_is_refused_until_forced(db_session):
    uid = await _user(db_session, "viewer")
    admin_id = await _user(db_session, "admin", "admin")
    rid = await _request(db_session, uid, "approved")

    assert await update_request_status(db_session, rid, "available", admin_id) == {
        "error": "not_in_library",
    }
    assert (await _state(db_session, rid)).status == "approved"
    assert await _bell_types(db_session) == []

    result = await update_request_status(db_session, rid, "available", admin_id, force=True)

    assert result["success"] is True
    state = await _state(db_session, rid)
    assert state.status == "available"
    assert state.available_at is not None
    assert await _bell_types(db_session) == ["request_available"]


@pytest.mark.asyncio
async def test_title_in_emby_is_marked_without_confirmation(db_session):
    uid = await _user(db_session, "viewer")
    admin_id = await _user(db_session, "admin", "admin")
    rid = await _request(db_session, uid, "approved")
    await _in_emby(db_session)

    assert (await update_request_status(db_session, rid, "available", admin_id))["success"] is True
    assert (await _state(db_session, rid)).status == "available"


@pytest.mark.asyncio
@pytest.mark.parametrize(("served", "expected"), [(False, "not_in_library"), (True, None)])
async def test_series_follow_the_episode_rule(db_session, monkeypatch, served, expected):
    uid = await _user(db_session, "viewer")
    admin_id = await _user(db_session, "admin", "admin")
    rid = await _request(db_session, uid, "approved", media_type="tv")
    await _in_emby(db_session, "tv")

    async def fake_served(db, req, series_ids, ignored):
        assert series_ids == ["EMBY-1"]
        return served

    monkeypatch.setattr(requests_fulfill, "_series_request_served", fake_served)

    result = await update_request_status(db_session, rid, "available", admin_id)

    assert result.get("error") == expected


@pytest.mark.asyncio
async def test_unexpected_check_failure_leaves_the_admin_to_decide(db_session, monkeypatch):
    """Emby or TMDB outages read as a missing title; only an unexpected error
    in the check itself reports it as failed."""
    uid = await _user(db_session, "viewer")
    admin_id = await _user(db_session, "admin", "admin")
    rid = await _request(db_session, uid, "approved")

    async def broken(db, req):
        raise RuntimeError("unexpected failure")

    monkeypatch.setattr(requests_fulfill, "is_request_in_library", broken)

    assert await update_request_status(db_session, rid, "available", admin_id) == {
        "error": "library_check_failed",
    }


@pytest.mark.asyncio
async def test_undoing_availability_goes_back_to_approved_silently(db_session):
    uid = await _user(db_session, "viewer")
    first_admin = await _user(db_session, "admin", "admin")
    other_admin = await _user(db_session, "admin2", "admin")
    rid = await _request(
        db_session, uid, "available",
        approved_by=first_admin, available_at=datetime.now(timezone.utc),
    )

    assert (await update_request_status(db_session, rid, "approved", other_admin))["success"] is True

    state = await _state(db_session, rid)
    assert state.status == "approved"
    assert state.available_at is None
    assert state.approved_by == first_admin  # who approved it does not change
    assert await _bell_types(db_session) == []


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["approved", "available", "rejected"])
async def test_resending_the_current_status_changes_nothing(db_session, status):
    """A stale queue line (the automatic flip got there first, another admin
    acted) resends the status the request already has: no bell, no rewrite."""
    uid = await _user(db_session, "viewer")
    first_admin = await _user(db_session, "admin", "admin")
    other_admin = await _user(db_session, "admin2", "admin")
    rid = await _request(
        db_session, uid, status, approved_by=first_admin, reject_reason="First reason",
        available_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        archived_at=datetime(2026, 2, 1, tzinfo=timezone.utc),  # stays archived too
    )
    before = await _row(db_session, rid)

    result = await update_request_status(
        db_session, rid, status, other_admin, "Second reason", force=True,
    )

    assert result == {"success": True, "user_id": uid}
    assert await _row(db_session, rid) == before
    assert await _bell_types(db_session) == []


@pytest.mark.asyncio
async def test_status_route_answers_409_until_forced(client, db_session):
    uid = await _user(db_session, "viewer")
    await _user(db_session, "boss", "admin")
    rid = await _request(db_session, uid, "approved")
    client.cookies.set("rq_token", create_access_token({"sub": "boss", "scope": "portal"}))

    refused = await client.put(f"/api/portal/requests/{rid}/status", json={"status": "available"})
    forced = await client.put(
        f"/api/portal/requests/{rid}/status", json={"status": "available", "force": True},
    )

    assert refused.status_code == 409
    assert refused.json()["detail"] == "not_in_library"
    assert forced.status_code == 200


@pytest.mark.asyncio
async def test_status_route_answers_404_for_an_unknown_request(client, db_session):
    await _user(db_session, "boss", "admin")
    client.cookies.set("rq_token", create_access_token({"sub": "boss", "scope": "portal"}))

    resp = await client.put("/api/portal/requests/999999/status", json={"status": "approved"})

    assert resp.status_code == 404
    assert resp.json()["detail"] == "not_found"
