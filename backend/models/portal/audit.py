"""Admin audit log: every action taken on a user profile is appended here.

Stays append-only: rows are never updated nor deleted, even when the
target user is removed (we keep ``target_user_id`` as a plain integer
without an FK so the trail survives soft-delete and hard-delete).
"""
from sqlalchemy import Column, Integer, String, JSON, DateTime
from datetime import datetime, timezone
from models.base import Base


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_log"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    admin_user_id   = Column(Integer, nullable=True, index=True)
    target_user_id  = Column(Integer, nullable=True, index=True)
    action          = Column(String(64), nullable=False, index=True)
    payload         = Column(JSON, nullable=True)
    ip              = Column(String(64), nullable=True)
    user_agent      = Column(String(255), nullable=True)
    created_at      = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
