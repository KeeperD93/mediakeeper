from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime, timezone
from models.base import Base


class IgnoredDoublon(Base):
    """
    Stores duplicates ignored by the user.
    duplicate_key = unique signature of the duplicate (e.g. "item_id_N" or normalized title).
    """
    __tablename__ = "ignored_doublons"

    id          = Column(Integer, primary_key=True, index=True)
    doublon_key = Column(String(500), nullable=False, unique=True, index=True)
    title       = Column(String(500), nullable=True)
    ignored_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
