from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey,
    UniqueConstraint,
)
from datetime import datetime, timezone
from models.base import Base


class News(Base):
    __tablename__ = "news"

    id              = Column(Integer, primary_key=True, index=True)
    # ``author_id`` becomes nullable + ``ON DELETE SET NULL`` from
    # migration 041 onwards. News articles are admin-authored
    # announcements visible to every user — their value is fully
    # detached from the author identity, so a purge anonymises but
    # never erases the post.
    author_id       = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"),
                             nullable=True)
    title           = Column(String(300), nullable=False)
    content         = Column(Text, nullable=False)
    image_url       = Column(String(500), nullable=True)
    type            = Column(String(30), server_default="announcement",
                             nullable=False, index=True)
    pinned          = Column(Boolean, server_default="false", nullable=False)
    notify_discord  = Column(Boolean, server_default="false", nullable=False)
    created_at      = Column(DateTime(timezone=True),
                             default=lambda: datetime.now(timezone.utc))
    updated_at      = Column(DateTime(timezone=True),
                             default=lambda: datetime.now(timezone.utc),
                             onupdate=lambda: datetime.now(timezone.utc))


class NewsRead(Base):
    __tablename__ = "news_reads"
    __table_args__ = (
        UniqueConstraint("news_id", "user_id", name="uq_news_read"),
    )

    id        = Column(Integer, primary_key=True, index=True)
    news_id   = Column(Integer, ForeignKey("news.id", ondelete="CASCADE"),
                       nullable=False, index=True)
    user_id   = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                       nullable=False)
    read_at   = Column(DateTime(timezone=True),
                       default=lambda: datetime.now(timezone.utc))
    dismissed = Column(Boolean, server_default="false", nullable=False)
