from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text,
)

from models.base import Base


class FeedbackReport(Base):
    """A bug/suggestion submitted by a delegated portal user, awaiting the
    admin's validation. Admin-submitted reports relay straight to Discord and
    are NOT stored here — this table only holds the delegate moderation queue.
    Rejected rows keep ``rejected_at`` and are purged after 30 days.
    """

    __tablename__ = "feedback_reports"

    id = Column(Integer, primary_key=True)
    reporter_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    reporter_name = Column(String(100), nullable=True)  # display name at submit time
    type = Column(String(20), server_default="bug", nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    reproduction = Column(Text, nullable=True)
    zone = Column(String(120), nullable=True)
    module = Column(String(120), nullable=True)
    tab = Column(String(120), nullable=True)
    platform = Column(String(20), nullable=True)
    resolution = Column(String(40), nullable=True)
    tags = Column(JSON, nullable=True)
    anonymous = Column(Boolean, server_default="false", nullable=False)
    status = Column(String(20), server_default="pending", nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    rejected_at = Column(DateTime(timezone=True), nullable=True, index=True)
