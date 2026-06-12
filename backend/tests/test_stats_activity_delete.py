"""Activity delete + bulk-delete endpoints — hardening:
extra=forbid, bounded id list, single-statement bulk delete, 404 on a
missing row. Admin-gated routes, exercised through ``authed_client``.
"""
import pytest
from sqlalchemy import select

from models.playback_stats import PlaybackSession


def _row(rid: int) -> PlaybackSession:
    return PlaybackSession(
        id=rid, session_key=f"s{rid}", user_id="u1", user_name="Alice",
        item_id="m1", item_name="Film", item_type="Movie",
    )


async def _remaining_ids(db_session) -> set[int]:
    rows = (await db_session.execute(select(PlaybackSession.id))).scalars().all()
    return set(rows)


@pytest.mark.asyncio
async def test_bulk_delete_removes_rows_and_reports_count(authed_client, db_session):
    db_session.add_all([_row(1), _row(2), _row(3)])
    await db_session.commit()
    r = await authed_client.post("/api/stats/activity/bulk-delete", json={"ids": [1, 2, 99]})
    assert r.status_code == 200
    assert r.json() == {"ok": True, "deleted": 2}  # id 99 absent -> not counted
    assert await _remaining_ids(db_session) == {3}


@pytest.mark.asyncio
async def test_bulk_delete_rejects_unknown_field(authed_client):
    r = await authed_client.post(
        "/api/stats/activity/bulk-delete", json={"ids": [1], "drop": True}
    )
    assert r.status_code == 422  # extra="forbid"


@pytest.mark.asyncio
async def test_bulk_delete_rejects_empty_and_oversized(authed_client):
    empty = await authed_client.post("/api/stats/activity/bulk-delete", json={"ids": []})
    assert empty.status_code == 422  # min_length=1
    oversized = await authed_client.post(
        "/api/stats/activity/bulk-delete", json={"ids": list(range(1001))}
    )
    assert oversized.status_code == 422  # max_length=1000


@pytest.mark.asyncio
async def test_bulk_delete_handles_the_max_bound(authed_client, db_session):
    """The declared 1000-id ceiling deletes in a single statement — guards
    against an IN-clause parameter-limit blowup at the boundary."""
    db_session.add_all([_row(i) for i in range(1, 1001)])
    await db_session.commit()
    r = await authed_client.post(
        "/api/stats/activity/bulk-delete", json={"ids": list(range(1, 1001))}
    )
    assert r.status_code == 200
    assert r.json() == {"ok": True, "deleted": 1000}
    assert await _remaining_ids(db_session) == set()


@pytest.mark.asyncio
async def test_delete_single_missing_returns_404(authed_client):
    r = await authed_client.delete("/api/stats/activity/424242")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_single_removes_row(authed_client, db_session):
    db_session.add(_row(7))
    await db_session.commit()
    r = await authed_client.delete("/api/stats/activity/7")
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    assert await _remaining_ids(db_session) == set()
