"""Offset pagination on GET /api/portal/tickets (page/per_page)."""

import pytest

from models.portal.ticket import Ticket
from tests._portal_profile_helpers import PORTAL_COOKIE, make_portal_user, portal_token


async def _seed_user(client, db_session, *, role="viewer"):
    user, _ = await make_portal_user(db_session, username="ticketer", role=role)
    client.cookies.set(PORTAL_COOKIE, portal_token("ticketer"))
    return user


async def _seed_tickets(db_session, user, count):
    db_session.add_all([
        Ticket(
            user_id=user.id,
            media_title=f"Movie {i:02d}",
            media_type="movie",
            issue_type="video",
            description="x",
            priority="minor",
            status="open",
        )
        for i in range(count)
    ])
    await db_session.commit()


@pytest.mark.asyncio
async def test_offset_pagination_walks_all_tickets(client, db_session):
    user = await _seed_user(client, db_session)
    await _seed_tickets(db_session, user, 25)

    seen: list[int] = []
    for page in (1, 2, 3):
        resp = await client.get(f"/api/portal/tickets?page={page}&per_page=10")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 25
        assert body["page"] == page
        assert body["per_page"] == 10
        seen.extend(t["id"] for t in body["items"])

    # 10 + 10 + 5 with no overlap and no skipped row.
    assert len(seen) == 25
    assert len(set(seen)) == 25


@pytest.mark.asyncio
async def test_sort_newest_is_reverse_of_oldest(client, db_session):
    user = await _seed_user(client, db_session)
    await _seed_tickets(db_session, user, 5)

    newest = await client.get("/api/portal/tickets?sort=newest&page=1&per_page=10")
    oldest = await client.get("/api/portal/tickets?sort=oldest&page=1&per_page=10")
    newest_ids = [t["id"] for t in newest.json()["items"]]
    oldest_ids = [t["id"] for t in oldest.json()["items"]]

    assert newest_ids == list(reversed(oldest_ids))
    assert newest_ids[0] == max(newest_ids)


@pytest.mark.asyncio
async def test_invalid_pagination_params_return_422(client, db_session):
    await _seed_user(client, db_session)
    for query in ("page=0", "per_page=0", "per_page=101"):
        resp = await client.get(f"/api/portal/tickets?{query}")
        assert resp.status_code == 422, query
