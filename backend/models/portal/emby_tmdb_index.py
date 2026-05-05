from sqlalchemy import Column, Integer, SmallInteger, String, DateTime
from datetime import datetime, timezone
from models.base import Base


class EmbyTmdbIndex(Base):
    __tablename__ = "emby_tmdb_index"

    id                 = Column(Integer, primary_key=True, index=True)
    emby_item_id       = Column(String(64), nullable=False, unique=True, index=True)
    tmdb_id            = Column(Integer, nullable=False, index=True)
    media_type         = Column(String(20), nullable=False)
    title              = Column(String(500), nullable=True)
    # Cached from Emby (already in /Items payload) — drives decades_watched
    # and secret_classic checks without a per-query TMDB roundtrip.
    production_year    = Column(SmallInteger, nullable=True)
    # ISO 639-1 from TMDB. Filled lazily by the sync; compared against the
    # PlaybackSession audio track (ISO 639-2) via iso_lang_map helpers.
    original_language  = Column(String(2), nullable=True)
    updated_at         = Column(DateTime(timezone=True),
                                default=lambda: datetime.now(timezone.utc),
                                onupdate=lambda: datetime.now(timezone.utc))
