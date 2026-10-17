"""Archived requests leave the Requests lists but stay counted: the lists, the
poster status and the duplicate checks ignore them, the admin totals keep
them, a blacklist unblock archives the media's rejections instead of
deleting them, and a status change brings an archived request back."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from core.security import hash_password
from models.portal.emby_tmdb_index import EmbyTmdbIndex
from models.portal.request import MediaRequest, RequestBlacklist
from models.user import User
from services.portal.admin import get_admin_stats
from services.portal.requests import get_batch_status, list_requests, update_request_status
from services.portal.requests_blacklist import reject_count, unblock_media
from services.portal.requests_create import create_request

ARCHIVED_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)


async def _user(db, username: str = "viewer") -> int:
    user = User(
        username=username,
        hashed_password=hash_password("Irrelevant123!"),
        is_active=True,
        must_change_password=False,
    )
    db.add(user)
    await db.commit()
    return user.id


async def _request(db, user_id: int, tmdb_id: int, status: str, *, archived: bool = False) -> int:
    req = MediaRequest(
        user_id=user_id, tmdb_id=tmdb_id, media_type="movie", title=f"Title {tmdb_id}",
        status=status, archived_at=ARCHIVED_AT if archived else None,
    )
    db.add(req)
    await db.commit()
    return req.id


def _ask(tmdb_id: int) -> dict:
    return {"tmdb_id": tmdb_id, "media_type": "movie", "title": f"Title {tmdb_id}"}


@pytest.mark.asyncio
async def test_lists_leave_archived_requests_out(db_session):
    uid = await _user(db_session)
    visible = await _request(db_session, uid, 1, "available")
    await _request(db_session, uid, 2, "available", archived=True)

    feed = await list_requests(db_session)
    queue = await list_requests(db_session, page=1)

    assert [i["id"] for i in feed["items"]] == [visible]
    assert [i["id"] for i in queue["items"]] == [visible]
    assert feed["total"] == queue["total"] == 1


@pytest.mark.asyncio
async def test_poster_status_ignores_archived_requests(db_session):
    uid = await _user(db_session)
    await _request(db_session, uid, 1, "available", archived=True)
    await _request(db_session, uid, 2, "rejected", archived=True)
    await _request(db_session, uid, 3, "available")

    assert set(await get_batch_status(db_session, [1, 2, 3])) == {"3"}


@pytest.mark.asyncio
async def test_admin_totals_keep_archived_requests(db_session):
    uid = await _user(db_session)
    await _request(db_session, uid, 1, "available")
    await _request(db_session, uid, 2, "available", archived=True)
    await _request(db_session, uid, 3, "rejected", archived=True)
    await _request(db_session, uid, 4, "pending")

    stats = await get_admin_stats(db_session)

    assert stats["available_count"] == 1  # what the queue still shows
    assert stats["available_total"] == 2
    assert stats["approved_total"] == 2
    assert stats["rejected_total"] == 1
    assert stats["total_requests"] == 4


@pytest.mark.asyncio
async def test_archived_request_no_longer_blocks_a_new_one(db_session):
    uid = await _user(db_session)
    await _request(db_session, uid, 1, "available", archived=True)

    result = await create_request(db_session, uid, _ask(1))

    assert result["success"] is True


@pytest.mark.asyncio
async def test_archived_rejection_stays_history(db_session):
    uid = await _user(db_session)
    old = await _request(db_session, uid, 1, "rejected", archived=True)

    result = await create_request(db_session, uid, _ask(1))

    assert result["success"] is True
    assert result["id"] != old
    first = (await db_session.execute(
        select(MediaRequest.status, MediaRequest.archived_at).where(MediaRequest.id == old)
    )).one()
    assert first.status == "rejected"
    assert first.archived_at is not None


@pytest.mark.asyncio
async def test_unblock_archives_rejections_and_restarts_the_count(db_session):
    uid = await _user(db_session)
    ids = [await _request(db_session, uid, 1, "rejected") for _ in range(3)]
    entry = RequestBlacklist(tmdb_id=1, media_type="movie", title="Title 1", reject_count=3)
    db_session.add(entry)
    await db_session.commit()

    assert await unblock_media(db_session, entry.id) == {"success": True}

    assert await reject_count(db_session, 1, "movie") == 0
    archived = (await db_session.execute(
        select(MediaRequest.id).where(MediaRequest.archived_at.is_not(None))
    )).scalars().all()
    assert sorted(archived) == ids
    assert (await get_admin_stats(db_session))["rejected_total"] == 3


@pytest.mark.asyncio
async def test_status_change_brings_an_archived_request_back(db_session):
    """Undoing the availability from a queue line archived meanwhile: the
    request comes back instead of hiding while it blocks the title."""
    uid = await _user(db_session)
    admin_id = await _user(db_session, "admin")
    rid = await _request(db_session, uid, 1, "available", archived=True)

    assert (await update_request_status(db_session, rid, "approved", admin_id))["success"] is True

    queue = await list_requests(db_session, page=1)
    assert [i["id"] for i in queue["items"]] == [rid]
    assert set(await get_batch_status(db_session, [1])) == {"1"}


@pytest.mark.asyncio
async def test_marking_available_by_hand_starts_the_archive_delay(db_session):
    uid = await _user(db_session)
    admin_id = await _user(db_session, "admin")
    rid = await _request(db_session, uid, 1, "approved")
    db_session.add(EmbyTmdbIndex(emby_item_id="EMBY-1", tmdb_id=1, media_type="movie"))
    await db_session.commit()

    async def available_at():
        return (await db_session.execute(
            select(MediaRequest.available_at).where(MediaRequest.id == rid)
        )).scalar_one()

    await update_request_status(db_session, rid, "available", admin_id)
    first = await available_at()
    await update_request_status(db_session, rid, "available", admin_id)

    assert first is not None
    assert await available_at() == first  # re-marking keeps the delay running
