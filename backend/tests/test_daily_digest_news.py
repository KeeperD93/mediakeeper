"""News in the daily digest, and reading one of them."""
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from constants.daily_digest import NEWS_LIMIT
from models.portal.news import News, NewsRead
from services.portal import daily_digest_sources as sources
from services.portal import news as news_svc
from tests._portal_profile_helpers import PORTAL_COOKIE, make_portal_user, portal_token

NOW = datetime.now(UTC)


def _news(title: str, *, pinned: bool = False, start_at=None, end_at=None) -> News:
    # Booleans set on purpose: the SQLite test base reads a "false" server default as true.
    return News(
        title=title, content="First paragraph.\n\nSecond paragraph.", type="announcement",
        pinned=pinned, notify_discord=False, start_at=start_at, end_at=end_at,
    )


async def _new_flags(db, user_id: int) -> dict[str, bool]:
    return {item["title"]: item["is_new"] for item in await sources.latest_news(db, user_id)}


@pytest.mark.asyncio
async def test_the_digest_lists_live_news_pinned_first(db_session):
    alice, _ = await make_portal_user(db_session, username="alice")
    db_session.add_all([
        _news("Old pinned", pinned=True),
        _news("Live"),
        _news("Not yet", start_at=NOW + timedelta(hours=1)),
        _news("Ended", end_at=NOW - timedelta(minutes=1)),
        _news("In its window", start_at=NOW - timedelta(days=1), end_at=NOW + timedelta(days=1)),
    ])
    await db_session.commit()

    items = await sources.latest_news(db_session, alice.id)

    assert [item["title"] for item in items] == ["Old pinned", "In its window", "Live"]
    assert items[0] | {"id": None, "created_at": None} == {
        "id": None, "title": "Old pinned", "content": "First paragraph.\n\nSecond paragraph.",
        "image_url": None, "type": "announcement", "pinned": True, "created_at": None,
        "is_new": True,
    }
    assert datetime.fromisoformat(items[0]["created_at"]).tzinfo is not None


@pytest.mark.asyncio
async def test_the_digest_keeps_the_five_newest_news(db_session):
    alice, _ = await make_portal_user(db_session, username="alice")
    db_session.add_all(_news(f"News {idx}") for idx in range(NEWS_LIMIT + 2))
    await db_session.commit()

    items = await sources.latest_news(db_session, alice.id)

    assert [item["title"] for item in items] == [f"News {idx}" for idx in range(6, 1, -1)]


@pytest.mark.asyncio
async def test_reading_a_news_clears_its_new_flag_for_this_account_only(client, db_session):
    alice, _ = await make_portal_user(db_session, username="alice")
    bob, _ = await make_portal_user(db_session, username="bob")
    first, second = _news("First"), _news("Second")
    db_session.add_all([first, second])
    await db_session.commit()
    db_session.add(NewsRead(news_id=second.id, user_id=bob.id, dismissed=False))
    await db_session.commit()
    client.cookies.set(PORTAL_COOKIE, portal_token(alice.username))

    assert await _new_flags(db_session, alice.id) == {"First": True, "Second": True}
    for _ in range(2):  # a second read updates the same row
        resp = await client.post(f"/api/portal/news/read/{first.id}")
        assert resp.status_code == 200, resp.text
    assert await _new_flags(db_session, alice.id) == {"First": False, "Second": True}


@pytest.mark.asyncio
async def test_reading_an_unknown_news_is_not_found(client, db_session):
    alice, _ = await make_portal_user(db_session, username="alice")
    client.cookies.set(PORTAL_COOKIE, portal_token(alice.username))

    resp = await client.post("/api/portal/news/read/12345")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "not_found"


@pytest.mark.asyncio
async def test_a_concurrent_first_read_updates_the_winning_row(db_session, monkeypatch):
    alice, _ = await make_portal_user(db_session, username="alice")
    news = _news("Raced")
    db_session.add(news)
    await db_session.commit()
    db_session.add(NewsRead(news_id=news.id, user_id=alice.id, dismissed=False))
    await db_session.commit()
    real_get_read = news_svc._get_read
    lookups: list[int] = []

    async def _missed_first(db, news_id, user_id):
        # The first lookup misses the row another request is inserting.
        lookups.append(news_id)
        return None if len(lookups) == 1 else await real_get_read(db, news_id, user_id)

    monkeypatch.setattr(news_svc, "_get_read", _missed_first)

    assert await news_svc.mark_news_read(db_session, news.id, alice.id, dismissed=True) == {
        "success": True,
    }
    rows = (await db_session.execute(
        select(NewsRead.dismissed).where(NewsRead.news_id == news.id)
    )).scalars().all()
    assert rows == [True]


@pytest.mark.asyncio
async def test_reading_never_brings_back_a_dismissed_news(db_session):
    alice, _ = await make_portal_user(db_session, username="alice")
    news = _news("Dismissed")
    db_session.add(news)
    await db_session.commit()

    await news_svc.mark_news_read(db_session, news.id, alice.id, dismissed=True)
    await news_svc.mark_news_read(db_session, news.id, alice.id)

    rows = (await db_session.execute(
        select(NewsRead.dismissed).where(NewsRead.news_id == news.id)
    )).scalars().all()
    assert rows == [True]


@pytest.mark.asyncio
@pytest.mark.parametrize("news_id", [0, 2_147_483_648])
async def test_reading_an_out_of_range_news_id_is_refused(client, db_session, news_id):
    alice, _ = await make_portal_user(db_session, username="alice")
    client.cookies.set(PORTAL_COOKIE, portal_token(alice.username))

    assert (await client.post(f"/api/portal/news/read/{news_id}")).status_code == 422
