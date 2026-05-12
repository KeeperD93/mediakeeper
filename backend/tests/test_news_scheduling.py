"""Schedule-aware news visibility (migration 045)."""
import pytest
from datetime import datetime, timedelta, timezone
from pydantic import ValidationError

from models.portal.news import News
from services.portal import news as news_svc
from api.portal.news import CreateNews


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_future_news_is_hidden_from_users_visible_to_admin(db_session):
    db_session.add(
        News(
            author_id=None,
            title="Future post",
            content="Soon™",
            type="announcement",
            start_at=_utcnow() + timedelta(days=2),
        )
    )
    await db_session.commit()

    user_view = await news_svc.list_news(db_session, respect_schedule=True)
    admin_view = await news_svc.list_news(db_session, respect_schedule=False)

    assert all(item["title"] != "Future post" for item in user_view["items"])
    assert any(item["title"] == "Future post" for item in admin_view["items"])


@pytest.mark.asyncio
async def test_expired_news_is_hidden_from_users_visible_to_admin(db_session):
    db_session.add(
        News(
            author_id=None,
            title="Old promo",
            content="Done",
            type="announcement",
            end_at=_utcnow() - timedelta(hours=1),
        )
    )
    await db_session.commit()

    user_view = await news_svc.list_news(db_session, respect_schedule=True)
    admin_view = await news_svc.list_news(db_session, respect_schedule=False)

    assert all(item["title"] != "Old promo" for item in user_view["items"])
    assert any(item["title"] == "Old promo" for item in admin_view["items"])


@pytest.mark.asyncio
async def test_active_window_news_visible_to_both(db_session):
    now = _utcnow()
    db_session.add(
        News(
            author_id=None,
            title="Live now",
            content="Active window",
            type="announcement",
            start_at=now - timedelta(hours=1),
            end_at=now + timedelta(hours=2),
        )
    )
    await db_session.commit()

    user_view = await news_svc.list_news(db_session, respect_schedule=True)
    admin_view = await news_svc.list_news(db_session, respect_schedule=False)

    assert any(item["title"] == "Live now" for item in user_view["items"])
    assert any(item["title"] == "Live now" for item in admin_view["items"])


@pytest.mark.asyncio
async def test_create_with_start_after_end_raises(db_session):
    now = _utcnow()
    with pytest.raises(ValueError):
        await news_svc.create_news(
            db_session,
            author_id=1,
            data={
                "title": "Bad window",
                "content": "x",
                "start_at": now + timedelta(days=2),
                "end_at": now + timedelta(days=1),
            },
        )


def test_pydantic_schema_accepts_optional_dates():
    payload = CreateNews(title="t", content="c")
    assert payload.start_at is None
    assert payload.end_at is None


def test_pydantic_schema_forbids_unknown_fields():
    with pytest.raises(ValidationError):
        CreateNews(title="t", content="c", unknown_field="x")
