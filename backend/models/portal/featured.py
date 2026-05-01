from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey
from datetime import datetime, timezone
from models.base import Base


class FeaturedHero(Base):
    __tablename__ = "featured_heroes"

    id          = Column(Integer, primary_key=True, index=True)
    tmdb_id     = Column(Integer, nullable=False)
    media_type  = Column(String(20), nullable=False)
    title       = Column(String(500), nullable=False)
    overview    = Column(Text, nullable=True)
    poster_url  = Column(String(500), nullable=True)
    backdrop    = Column(String(500), nullable=True)
    vote        = Column(Float, nullable=True)
    year        = Column(String(10), nullable=True)
    sort_order  = Column(Integer, server_default="0", nullable=False)
    active      = Column(Boolean, server_default="true", nullable=False)
    added_by    = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
