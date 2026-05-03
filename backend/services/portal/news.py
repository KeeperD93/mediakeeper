"""News and announcements system."""
import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.news import News, NewsRead
from core.pagination import decode_cursor, build_cursor_response
from services.portal import strip_tags_and_trim

logger = logging.getLogger("mediakeeper.portal.news")


async def create_news(db: AsyncSession, author_id: int, data: dict) -> dict:
    article = News(
        author_id=author_id,
        title=strip_tags_and_trim(data["title"], 300),
        content=strip_tags_and_trim(data["content"], 10000),
        image_url=data.get("image_url"),
        type=data.get("type", "announcement"),
        pinned=data.get("pinned", False),
        notify_discord=data.get("notify_discord", False),
    )
    db.add(article)
    await db.commit()
    await db.refresh(article)
    logger.info(f"[NEWS] #{article.id} created by user_id={author_id}")
    return {"success": True, "id": article.id}


async def list_news(
    db: AsyncSession,
    cursor: str | None = None,
    limit: int = 20,
) -> dict:
    query = select(News).order_by(News.pinned.desc(), News.id.desc())
    count_q = select(func.count(News.id))

    cursor_data = decode_cursor(cursor)
    if cursor_data and cursor_data.get("id"):
        query = query.where(News.id < cursor_data["id"])

    total = (await db.execute(count_q)).scalar() or 0
    items = [_serialize(n) for n in (await db.execute(query.limit(limit))).scalars().all()]
    return build_cursor_response(items, total, limit)


async def get_unread_news(db: AsyncSession, user_id: int) -> list[dict]:
    """Get news not yet dismissed by user (for login popup)."""
    subq = (
        select(NewsRead.news_id)
        .where(NewsRead.user_id == user_id, NewsRead.dismissed == True)  # noqa: E712
    )
    result = await db.execute(
        select(News)
        .where(News.id.notin_(subq))
        .order_by(News.pinned.desc(), News.id.desc())
        .limit(10)
    )
    return [_serialize(n) for n in result.scalars().all()]


async def mark_news_read(
    db: AsyncSession, news_id: int, user_id: int, dismissed: bool = False
) -> dict:
    existing = await db.execute(
        select(NewsRead).where(
            NewsRead.news_id == news_id,
            NewsRead.user_id == user_id,
        )
    )
    read = existing.scalar_one_or_none()
    if read:
        read.dismissed = dismissed
    else:
        read = NewsRead(news_id=news_id, user_id=user_id, dismissed=dismissed)
    db.add(read)
    await db.commit()
    return {"success": True}


async def update_news(db: AsyncSession, news_id: int, data: dict) -> dict:
    article = await db.get(News, news_id)
    if not article:
        return {"error": "not_found"}
    for key in ("title", "content", "image_url", "type", "pinned", "notify_discord"):
        if key in data:
            val = data[key]
            if key in ("title", "content") and isinstance(val, str):
                val = strip_tags_and_trim(val, 10000 if key == "content" else 300)
            setattr(article, key, val)
    db.add(article)
    await db.commit()
    return {"success": True}


async def delete_news(db: AsyncSession, news_id: int) -> dict:
    article = await db.get(News, news_id)
    if not article:
        return {"error": "not_found"}
    await db.delete(article)
    await db.commit()
    logger.info(f"[NEWS] #{news_id} deleted")
    return {"success": True}


def _serialize(n: News) -> dict:
    return {
        "id": n.id,
        "author_id": n.author_id,
        "title": n.title,
        "content": n.content,
        "image_url": n.image_url,
        "type": n.type,
        "pinned": n.pinned,
        "created_at": n.created_at.isoformat() if n.created_at else None,
        "updated_at": n.updated_at.isoformat() if n.updated_at else None,
    }
