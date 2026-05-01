from sqlalchemy import Column, Integer, String, BigInteger, DateTime
from datetime import datetime, timezone
from models.base import Base


class DoublonCleanup(Base):
    """Log of duplicate cleanups performed."""
    __tablename__ = "doublon_cleanups"

    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String(500), nullable=True)
    filename    = Column(String(1000), nullable=True)
    size_bytes  = Column(BigInteger, default=0)
    action      = Column(String(50), default="deleted")  # deleted, kept
    created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
