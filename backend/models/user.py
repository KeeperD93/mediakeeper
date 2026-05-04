from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime, timezone
from models.base import Base


class User(Base):
    __tablename__ = "users"

    id                   = Column(Integer, primary_key=True, index=True)
    username             = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password      = Column(String(255), nullable=False)
    is_active            = Column(Boolean, default=True, nullable=False)
    must_change_password = Column(Boolean, default=True, nullable=False)
    tokens_invalidated_at = Column(DateTime(timezone=True), nullable=True)
    # GDPR self-service deletion (Batch 11B). ``deletion_requested_at``
    # records when the user submitted the request; ``pending_deletion_at``
    # is the wall-clock at which the purge job is allowed to hard-delete
    # the row. Both stay NULL on a normal account.
    deletion_requested_at = Column(DateTime(timezone=True), nullable=True)
    pending_deletion_at  = Column(DateTime(timezone=True), nullable=True)
    created_at           = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at           = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
