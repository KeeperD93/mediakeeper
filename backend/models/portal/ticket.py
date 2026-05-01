from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from datetime import datetime, timezone
from models.base import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    emby_item_id    = Column(String(64), nullable=True)
    series_emby_id  = Column(String(64), nullable=True)
    tmdb_id         = Column(Integer, nullable=True)
    media_title     = Column(String(500), nullable=False)
    media_type      = Column(String(20), nullable=False)
    selected_seasons = Column(JSON, nullable=True)
    issue_type      = Column(String(30), nullable=False, index=True)
    priority        = Column(String(20), server_default="minor", nullable=False)
    description     = Column(Text, nullable=False)
    status          = Column(String(20), server_default="open",
                             nullable=False, index=True)
    created_at      = Column(DateTime(timezone=True),
                             default=lambda: datetime.now(timezone.utc))
    updated_at      = Column(DateTime(timezone=True),
                             default=lambda: datetime.now(timezone.utc),
                             onupdate=lambda: datetime.now(timezone.utc))


class TicketReply(Base):
    __tablename__ = "ticket_replies"

    id          = Column(Integer, primary_key=True, index=True)
    ticket_id   = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    user_id     = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                         nullable=False)
    content     = Column(Text, nullable=False)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc))
