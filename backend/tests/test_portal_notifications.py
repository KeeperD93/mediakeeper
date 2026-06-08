"""Cursor pagination on GET /api/portal/notifications (bell "load more")
plus the 6-month retention purge (services.portal.notifications.delete_old)."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from core.security import create_access_token
from models.portal.profile import UserProfile
from models.portal.event import MKNotification
from services.portal import notifications as notifs


async def _portal_cookie(client, user, db_session):
    db_session.add(UserProfile(
        user_id=user.id,
        display_name="User",
        role="user",
        account_active=True,
        chat_enabled=True,
    ))
    await db_session.commit()
    client.cookies.set(
        "rq_token",
        create_access_token({"sub": user.username, "scope": "portal"}),
    )


async def _seed(db_session, user, count, *, unread=False):
    db_session.add_all([
        MKNotification(
            user_id=user.id,
            type="event_invitation",
            payload={"i": i},
            read=not unread,
        )
        for i in range(count)
    ])
    await db_session.commit()


@pytest.mark.asyncio
async def test_cursor_walks_all_notifications_without_overlap(client, admin_user, db_session):
    await _portal_cookie(client, admin_user, db_session)
    await _seed(db_session, admin_user, 25)

    seen: list[int] = []
    cursor = None
    for _ in range(3):
        url = "/api/portal/notifications?limit=10"
        if cursor:
            url += f"&cursor={cursor}"
        resp = await client.get(url)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 25
        seen.extend(item["id"] for item in body["items"])
        cursor = body["next_cursor"]

    # 10 + 10 + 5 with no overlap and no skipped row.
    assert len(seen) == 25
    assert len(set(seen)) == 25
    # Newest-first: strictly descending ids across pages.
    assert seen == sorted(seen, reverse=True)


@pytest.mark.asyncio
async def test_default_page_size_is_ten(client, admin_user, db_session):
    await _portal_cookie(client, admin_user, db_session)
    await _seed(db_session, admin_user, 15)

    body = (await client.get("/api/portal/notifications")).json()
    assert len(body["items"]) == 10
    assert body["has_more"] is True


@pytest.mark.asyncio
async def test_has_more_flag_and_terminal_cursor(client, admin_user, db_session):
    await _portal_cookie(client, admin_user, db_session)
    await _seed(db_session, admin_user, 12)

    first = (await client.get("/api/portal/notifications?limit=10")).json()
    assert len(first["items"]) == 10
    assert first["has_more"] is True
    assert first["next_cursor"]

    second = (await client.get(
        f"/api/portal/notifications?limit=10&cursor={first['next_cursor']}"
    )).json()
    assert len(second["items"]) == 2
    assert second["has_more"] is False
    assert second["next_cursor"] is None


@pytest.mark.asyncio
async def test_unread_only_filters_items_and_total(client, admin_user, db_session):
    await _portal_cookie(client, admin_user, db_session)
    await _seed(db_session, admin_user, 3, unread=True)
    await _seed(db_session, admin_user, 5, unread=False)

    body = (await client.get("/api/portal/notifications?unread_only=true&limit=50")).json()
    assert body["total"] == 3
    assert all(item["read"] is False for item in body["items"])


@pytest.mark.asyncio
async def test_invalid_cursor_is_ignored_returns_first_page(client, admin_user, db_session):
    await _portal_cookie(client, admin_user, db_session)
    await _seed(db_session, admin_user, 4)

    body = (await client.get(
        "/api/portal/notifications?cursor=not-a-valid-cursor&limit=50"
    )).json()
    assert len(body["items"]) == 4
    assert body["total"] == 4


@pytest.mark.asyncio
async def test_invalid_limit_returns_422(client, admin_user, db_session):
    await _portal_cookie(client, admin_user, db_session)
    for query in ("limit=0", "limit=201"):
        resp = await client.get(f"/api/portal/notifications?{query}")
        assert resp.status_code == 422, query


@pytest.mark.asyncio
async def test_delete_old_purges_only_notifications_past_retention(db_session, admin_user):
    now = datetime.now(timezone.utc)
    db_session.add_all([
        MKNotification(user_id=admin_user.id, type="event_invitation", read=True,
                       created_at=now - timedelta(days=200)),
        MKNotification(user_id=admin_user.id, type="event_invitation", read=False,
                       created_at=now - timedelta(days=181)),
        MKNotification(user_id=admin_user.id, type="event_invitation", read=True,
                       created_at=now - timedelta(days=30)),
    ])
    await db_session.commit()

    # Default retention is 6 months: both >180d rows go, the 30d one stays.
    removed = await notifs.delete_old(db_session)
    await db_session.commit()
    assert removed == 2

    remaining = (await db_session.execute(
        select(MKNotification.id).where(MKNotification.user_id == admin_user.id)
    )).scalars().all()
    assert len(remaining) == 1
