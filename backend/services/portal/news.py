"""News and announcements system."""
import logging
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.portal.news import News, NewsRead
from core.pagination import decode_cursor, build_cursor_response
from services.portal import strip_tags_and_trim

logger = logging.getLogger("mediakeeper.portal.news")


def _validate_window(start_at, end_at) -> None:
    if start_at is not None and end_at is not None and start_at >= end_at:
        raise ValueError("start_at_must_precede_end_at")


def _active_window_clause(now):
    """SQLAlchemy clause keeping rows that overlap ``now``."""
    return (
        ((News.start_at.is_(None)) | (News.start_at <= now))
        & ((News.end_at.is_(None)) | (News.end_at > now))
    )


async def create_news(db: AsyncSession, author_id: int, data: dict) -> dict:
    start_at = data.get("start_at")
    end_at = data.get("end_at")
    _validate_window(start_at, end_at)
    article = News(
        author_id=author_id,
        title=strip_tags_and_trim(data["title"], 300),
        content=strip_tags_and_trim(data["content"], 10000),
        image_url=data.get("image_url"),
        type=data.get("type", "announcement"),
        pinned=data.get("pinned", False),
        notify_discord=data.get("notify_discord", False),
        start_at=start_at,
        end_at=end_at,
    )
    db.add(article)
    await db.commit()
    await db.refresh(article)
    logger.info("[NEWS] #%s created by user_id=%s", article.id, author_id)
    return {"success": True, "id": article.id}


async def list_news(
    db: AsyncSession,
    cursor: str | None = None,
    limit: int = 20,
    respect_schedule: bool = True,
) -> dict:
    query = select(News).order_by(News.pinned.desc(), News.id.desc())
    count_q = select(func.count(News.id))

    if respect_schedule:
        now = datetime.now(timezone.utc)
        active = _active_window_clause(now)
        query = query.where(active)
        count_q = count_q.where(active)

    cursor_data = decode_cursor(cursor)
    if cursor_data and cursor_data.get("id"):
        query = query.where(News.id < cursor_data["id"])

    total = (await db.execute(count_q)).scalar() or 0
    items = [_serialize(n) for n in (await db.execute(query.limit(limit))).scalars().all()]
    return build_cursor_response(items, total, limit)


async def get_unread_news(db: AsyncSession, user_id: int) -> list[dict]:
    """Get news not yet dismissed by user (for login popup).

    Honours the scheduling window so a future-dated or expired post
    never surfaces in the WhatsNew overlay.
    """
    now = datetime.now(timezone.utc)
    subq = (
        select(NewsRead.news_id)
        .where(NewsRead.user_id == user_id, NewsRead.dismissed == True)  # noqa: E712
    )
    result = await db.execute(
        select(News)
        .where(News.id.notin_(subq))
        .where(_active_window_clause(now))
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
    new_start = data["start_at"] if "start_at" in data else article.start_at
    new_end = data["end_at"] if "end_at" in data else article.end_at
    _validate_window(new_start, new_end)
    for key in (
        "title", "content", "image_url", "type", "pinned",
        "notify_discord", "start_at", "end_at",
    ):
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
    logger.info("[NEWS] #%s deleted", news_id)
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
        "start_at": n.start_at.isoformat() if n.start_at else None,
        "end_at": n.end_at.isoformat() if n.end_at else None,
        "created_at": n.created_at.isoformat() if n.created_at else None,
        "updated_at": n.updated_at.isoformat() if n.updated_at else None,
    }
