"""Security log: login attempts + IP/username blocks.

Replaces the in-memory ``_login_attempts`` dict so rate limiting survives
restarts, can be audited and manually overridden by an admin.
"""
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String

from models.base import Base


class SecurityAttempt(Base):
    """Single login attempt (success or failure).

    - ``scope`` is ``admin`` for the backoffice login, ``portal`` for the
      Emby-backed portal and ``admin_password`` for a password change. Failed
      attempts on unknown usernames still carry the username typed by the
      attacker so admins can spot credential-stuffing.
    - Rows older than 90 days are removed by the admin purge
      (``purge_old_attempts``).
    - ``cleared_at`` is set when an unblock or a later successful sign-in
      stops a failure from counting: it stays listed, no counter counts it.
    """
    __tablename__ = "security_attempts"

    id = Column(Integer, primary_key=True)
    ip = Column(String(64), nullable=False, index=True)
    username = Column(String(100), nullable=True, index=True)
    scope = Column(String(20), nullable=False)  # admin | admin_password | portal
    success = Column(Integer, nullable=False, default=0)  # 0/1 for portability
    user_agent = Column(String(300), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    cleared_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_security_attempts_ip_created", "ip", "created_at"),
        Index("ix_security_attempts_user_created", "username", "created_at"),
        CheckConstraint("success IN (0, 1)", name="ck_security_attempts_success_bool"),
    )


class SecurityBlock(Base):
    """Active block entry. A row matches on either ``ip`` or ``username``.

    - ``blocked_until`` NULL + ``permanent=1`` → perma-ban until the admin
      deletes the row.
    - ``blocked_until`` in the future + ``permanent=0`` → temporary block, set
      after too many failed attempts (or by an admin through the API).
    - ``automatic`` is 1 for the blocks set after repeated failed sign-ins and
      0 for an admin's own. ``created_by`` holds the admin's id on a manual
      block, but becomes NULL when that admin is deleted, so it cannot tell
      them apart.
    """
    __tablename__ = "security_blocks"

    id = Column(Integer, primary_key=True)
    ip = Column(String(64), nullable=True, index=True)
    username = Column(String(100), nullable=True, index=True)
    scope = Column(String(20), nullable=False)  # admin | admin_password | portal | all
    permanent = Column(Integer, nullable=False, default=0)
    # A column-level check: SQLite cannot drop a column named in a table-level one.
    automatic = Column(
        Integer,
        CheckConstraint("automatic IN (0, 1)", name="ck_security_blocks_automatic_bool"),
        nullable=False,
        default=0,
        server_default="0",
    )
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

    __table_args__ = (
        CheckConstraint("permanent IN (0, 1)", name="ck_security_blocks_permanent_bool"),
    )
