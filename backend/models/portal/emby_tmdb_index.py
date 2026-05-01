from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime, timezone
from models.base import Base


class EmbyTmdbIndex(Base):
    __tablename__ = "emby_tmdb_index"

    id            = Column(Integer, primary_key=True, index=True)
    emby_item_id  = Column(String(64), nullable=False, unique=True, index=True)
    tmdb_id       = Column(Integer, nullable=False, index=True)
    media_type    = Column(String(20), nullable=False)
    title         = Column(String(500), nullable=True)
    updated_at    = Column(DateTime(timezone=True),
                           default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
