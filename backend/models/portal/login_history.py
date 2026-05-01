"""Append-only login history for the Portal.

One row per attempt, success or failure, keyed by ``user_id`` when we
managed to identify the account (NULL for "unknown user" attempts —
brute-force probes etc.). Surfaced on the admin Security tab.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Index
from datetime import datetime, timezone
from models.base import Base


class UserLoginHistory(Base):
    __tablename__ = "user_login_history"
    __table_args__ = (
        Index("ix_user_login_history_user_created", "user_id", "created_at"),
    )

    id          = Column(Integer, primary_key=True, autoincrement=True)
    user_id     = Column(Integer, nullable=True, index=True)
    username    = Column(String(100), nullable=True)
    source      = Column(String(20), nullable=False)
    success     = Column(Boolean, nullable=False)
    ip          = Column(String(64), nullable=True)
    user_agent  = Column(String(255), nullable=True)
    created_at  = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
