from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON,
    UniqueConstraint,
)
from datetime import datetime, timezone
from models.base import Base


class MediaRequest(Base):
    __tablename__ = "media_requests"

    id              = Column(Integer, primary_key=True, index=True)
    # ``user_id`` becomes nullable + ``ON DELETE SET NULL`` from migration
    # 041 onwards: media requests carry significant admin/audit value
    # (queue history, blacklist trail) that must outlive the requester
    # disappearing. ``approved_by`` and ``requested_by_admin`` already
    # use SET NULL — this aligns ``user_id`` with the same policy.
    user_id         = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"),
                             nullable=True, index=True)
    tmdb_id         = Column(Integer, nullable=False, index=True)
    media_type      = Column(String(20), nullable=False)
    title           = Column(String(500), nullable=False)
    year            = Column(Integer, nullable=True)
    poster_url      = Column(String(500), nullable=True)
    backdrop_url    = Column(String(500), nullable=True)
    status          = Column(String(20), server_default="pending",
                             nullable=False, index=True)
    reject_reason   = Column(Text, nullable=True)
    retry_count     = Column(Integer, server_default="0", nullable=False)
    approved_by     = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"),
                             nullable=True)
    auto_approved   = Column(Boolean, server_default="false", nullable=False)
    requested_seasons = Column(JSON, nullable=True)
    requested_by_admin = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"),
                                nullable=True)
    created_at      = Column(DateTime(timezone=True),
                             default=lambda: datetime.now(timezone.utc))
    updated_at      = Column(DateTime(timezone=True),
                             default=lambda: datetime.now(timezone.utc),
                             onupdate=lambda: datetime.now(timezone.utc))
    # Stamped when the row flips to ``available`` so the auto-cleanup
    # job can window deletions on that moment exclusively (``updated_at``
    # is bumped on every status change).
    available_at    = Column(DateTime(timezone=True), nullable=True)


class RequestBlacklist(Base):
    """Media that was rejected 3 times — hidden from discover / genre feeds
    until an admin clears it. The requester history (JSON list of user ids +
    display names) is kept for transparency in the admin blacklist screen."""
    __tablename__ = "request_blacklist"
    __table_args__ = (
        UniqueConstraint("tmdb_id", "media_type", name="uq_blacklist_media"),
    )

    id              = Column(Integer, primary_key=True, index=True)
    tmdb_id         = Column(Integer, nullable=False, index=True)
    media_type      = Column(String(20), nullable=False)
    title           = Column(String(500), nullable=False)
    year            = Column(Integer, nullable=True)
    poster_url      = Column(String(500), nullable=True)
    requesters      = Column(JSON, nullable=True)  # [{user_id, display_name}]
    reject_count    = Column(Integer, server_default="3", nullable=False)
    blocked_at      = Column(DateTime(timezone=True),
                             default=lambda: datetime.now(timezone.utc))
    blocked_by      = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"),
                             nullable=True)


class RequestQuota(Base):
    __tablename__ = "request_quotas"

    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                           nullable=False, unique=True, index=True)
    month         = Column(String(7), nullable=False)
    used          = Column(Integer, server_default="0", nullable=False)
    max_allowed   = Column(Integer, server_default="5", nullable=False)
    # 'manual' = admin-set max_allowed ; 'auto' = nightly engagement-scored
    # cap that drifts within [auto_min, auto_max] (see services/portal/quota_auto).
    mode          = Column(String(20), server_default="manual", nullable=False)
    unlimited     = Column(Boolean, server_default="false", nullable=False)
    auto_approve  = Column(Boolean, server_default="false", nullable=False)
    # Per-user clamps for 'auto' mode (seeded from instance defaults, admin
    # may override per user). Ignored while mode='manual'.
    auto_min      = Column(Integer, server_default="2", nullable=False)
    auto_max      = Column(Integer, server_default="15", nullable=False)
    # Stamped by the nightly auto-recompute job; NULL until its first touch.
    last_recomputed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at    = Column(DateTime(timezone=True),
                           default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
