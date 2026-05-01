"""Security log: login attempts + IP/username blocks.

Replaces the in-memory ``_login_attempts`` dict so rate limiting survives
restarts, can be audited and manually overridden by an admin.
"""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String

from models.base import Base


class SecurityAttempt(Base):
    """Single login attempt (success or failure).

    - ``scope`` is ``admin`` for the backoffice login and ``portal`` for the
      Emby-backed portal. Failed attempts on unknown usernames still carry the
      username typed by the attacker so admins can spot credential-stuffing.
    - Rows are kept for 90 days and purged by the scheduler.
    """
    __tablename__ = "security_attempts"

    id = Column(Integer, primary_key=True)
    ip = Column(String(64), nullable=False, index=True)
    username = Column(String(100), nullable=True, index=True)
    scope = Column(String(20), nullable=False)  # admin | portal
    success = Column(Integer, nullable=False, default=0)  # 0/1 for portability
    user_agent = Column(String(300), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        Index("ix_security_attempts_ip_created", "ip", "created_at"),
        Index("ix_security_attempts_user_created", "username", "created_at"),
    )


class SecurityBlock(Base):
    """Active block entry. A row matches on either ``ip`` or ``username``.

    - ``blocked_until`` NULL + ``permanent=1`` → perma-ban until the admin
      deletes the row.
    - ``blocked_until`` in the future + ``permanent=0`` → automatic temporary
      block triggered by too many failed attempts.
    - ``created_by`` is NULL for auto-blocks, set to the admin user id for
      manual ones.
    """
    __tablename__ = "security_blocks"

    id = Column(Integer, primary_key=True)
    ip = Column(String(64), nullable=True, index=True)
    username = Column(String(100), nullable=True, index=True)
    scope = Column(String(20), nullable=False)  # admin | portal | all
    permanent = Column(Integer, nullable=False, default=0)
    blocked_until = Column(DateTime(timezone=True), nullable=True)
    reason = Column(String(200), nullable=True)
    created_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
