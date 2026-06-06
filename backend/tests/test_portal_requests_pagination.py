"""Offset pagination, sort and media-type filter on GET /api/portal/requests/admin."""

import pytest

from core.security import create_access_token
from models.portal.profile import UserProfile
from models.portal.request import MediaRequest


async def _admin_cookie(client, admin_user, db_session):
    db_session.add(UserProfile(
        user_id=admin_user.id,
        display_name="Admin",
        role="admin",
        account_active=True,
        chat_enabled=True,
    ))
    await db_session.commit()
    client.cookies.set(
        "rq_token",
        create_access_token({"sub": admin_user.username, "scope": "portal"}),
    )


async def _seed(db_session, admin_user, count, *, base, media_type="movie", title_prefix="Req"):
    db_session.add_all([
        MediaRequest(
            user_id=admin_user.id,
            tmdb_id=base + i,
            media_type=media_type,
            title=f"{title_prefix} {i:02d}",
            status="pending",
        )
        for i in range(count)
    ])
    await db_session.commit()


@pytest.mark.asyncio
async def test_offset_pagination_walks_all_requests(client, admin_user, db_session):
    await _admin_cookie(client, admin_user, db_session)
    await _seed(db_session, admin_user, 25, base=1000)

    seen: list[int] = []
    for page in (1, 2, 3):
        resp = await client.get(f"/api/portal/requests/admin?page={page}&per_page=10")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 25
        assert body["page"] == page
        assert body["per_page"] == 10
        seen.extend(item["id"] for item in body["items"])

    # 10 + 10 + 5 with no overlap and no skipped row.
    assert len(seen) == 25
    assert len(set(seen)) == 25


@pytest.mark.asyncio
async def test_sort_recent_is_reverse_of_oldest(client, admin_user, db_session):
    await _admin_cookie(client, admin_user, db_session)
    await _seed(db_session, admin_user, 5, base=2000)

    recent = await client.get("/api/portal/requests/admin?sort=recent&per_page=10")
    oldest = await client.get("/api/portal/requests/admin?sort=oldest&per_page=10")
    recent_ids = [i["id"] for i in recent.json()["items"]]
    oldest_ids = [i["id"] for i in oldest.json()["items"]]

    assert recent_ids == list(reversed(oldest_ids))
    assert recent_ids[0] == max(recent_ids)


@pytest.mark.asyncio
async def test_sort_title_is_case_insensitive_alphabetical(client, admin_user, db_session):
    await _admin_cookie(client, admin_user, db_session)
    db_session.add_all([
        MediaRequest(user_id=admin_user.id, tmdb_id=3001, media_type="movie", title="Zebra", status="pending"),
        MediaRequest(user_id=admin_user.id, tmdb_id=3002, media_type="movie", title="alpha", status="pending"),
        MediaRequest(user_id=admin_user.id, tmdb_id=3003, media_type="movie", title="Mango", status="pending"),
    ])
    await db_session.commit()

    resp = await client.get("/api/portal/requests/admin?sort=title&per_page=10")
    assert [i["title"] for i in resp.json()["items"]] == ["alpha", "Mango", "Zebra"]


@pytest.mark.asyncio
async def test_media_type_filter_scopes_items_and_total(client, admin_user, db_session):
    await _admin_cookie(client, admin_user, db_session)
    await _seed(db_session, admin_user, 3, base=4000, media_type="movie", title_prefix="Film")
    await _seed(db_session, admin_user, 2, base=5000, media_type="tv", title_prefix="Show")

    movies = (await client.get("/api/portal/requests/admin?type=movie&per_page=50")).json()
    assert movies["total"] == 3
    assert all(i["media_type"] == "movie" for i in movies["items"])

    series = (await client.get("/api/portal/requests/admin?type=tv&per_page=50")).json()
    assert series["total"] == 2
    assert all(i["media_type"] == "tv" for i in series["items"])


@pytest.mark.asyncio
async def test_invalid_pagination_params_return_422(client, admin_user, db_session):
    await _admin_cookie(client, admin_user, db_session)
    for query in ("per_page=101", "per_page=0", "page=0", "sort=bogus", "type=anime"):
        resp = await client.get(f"/api/portal/requests/admin?{query}")
        assert resp.status_code == 422, query
