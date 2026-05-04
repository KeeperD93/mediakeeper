from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey,
)
from datetime import datetime, timezone
from models.base import Base


class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    id                = Column(Integer, primary_key=True, index=True)
    type              = Column(String(20), nullable=False, index=True)
    name              = Column(String(100), nullable=False)
    linked_request_id = Column(Integer, ForeignKey("media_requests.id",
                               ondelete="SET NULL"), nullable=True)
    created_at        = Column(DateTime(timezone=True),
                               default=lambda: datetime.now(timezone.utc))


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id          = Column(Integer, primary_key=True, index=True)
    room_id     = Column(Integer, ForeignKey("chat_rooms.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    # ``user_id`` becomes nullable + ``ON DELETE SET NULL`` from migration
    # 040 onwards: when a GDPR purge hard-deletes the user, their messages
    # are anonymised instead of vanishing so the surrounding conversation
    # stays readable for the other participants.
    user_id     = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"),
                         nullable=True, index=True)
    content     = Column(Text, nullable=False)
    deleted     = Column(Boolean, server_default="false", nullable=False)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc))


class ChatMute(Base):
    __tablename__ = "chat_mutes"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                         nullable=False, unique=True, index=True)
    muted_until = Column(DateTime(timezone=True), nullable=False)
    reason      = Column(String(300), nullable=True)


class ChatReport(Base):
    """
    User-submitted flag on a specific chat message. Surfaced on the
    MediaKeeper admin dashboard (the bell) so moderators can review
    and either dismiss the report or delete the offending message.
    """
    __tablename__ = "chat_reports"

    id          = Column(Integer, primary_key=True, index=True)
    message_id  = Column(Integer, ForeignKey("chat_messages.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    # ``reporter_id`` becomes nullable + ``ON DELETE SET NULL`` from
    # migration 041 onwards: the moderation history (handled flag,
    # reason text) keeps its audit value even once the reporter is
    # purged. Notification payloads carry a snapshot pseudo so the
    # bell stays meaningful.
    reporter_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"),
                         nullable=True)
    reason      = Column(String(500), nullable=True)
    handled     = Column(Boolean, server_default="false", nullable=False)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc))
