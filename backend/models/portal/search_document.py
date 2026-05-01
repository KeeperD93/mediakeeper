from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, UniqueConstraint

from models.base import Base


class PortalSearchDocument(Base):
    __tablename__ = "portal_search_documents"
    __table_args__ = (
        UniqueConstraint("tmdb_id", "media_type", name="uq_portal_search_tmdb_media"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tmdb_id = Column(Integer, nullable=False, index=True)
    media_type = Column(String(20), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    original_title = Column(String(500), nullable=True)
    search_text = Column(Text, nullable=False)
    year = Column(Integer, nullable=True, index=True)
    overview = Column(Text, nullable=True)
    poster_url = Column(String(700), nullable=True)
    backdrop_url = Column(String(700), nullable=True)
    vote_average = Column(Float, nullable=False, default=0.0)
    popularity = Column(Float, nullable=False, default=0.0)
    genres = Column(Text, nullable=True)
    available_on_emby = Column(Boolean, nullable=False, default=False, index=True)
    source = Column(String(32), nullable=False, default="tmdb")
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
