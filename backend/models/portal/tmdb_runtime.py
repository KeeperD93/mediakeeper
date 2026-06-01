from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint
from datetime import datetime, timezone
from models.base import Base


class TmdbRuntimeCache(Base):
    """Persistent cache of TMDB runtimes (minutes), keyed by
    (tmdb_id, media_type).

    TMDB list endpoints (trending/popular/discover/search) never return a
    runtime — only the per-item detail endpoint does. Caching the resolved
    runtime here lets every portal poster card show a duration without an
    N+1 detail call per render, and survives restarts so the cache is not
    re-warmed on every boot.
    """
    __tablename__ = "tmdb_runtime_cache"

    id          = Column(Integer, primary_key=True)
    tmdb_id     = Column(Integer, nullable=False, index=True)
    media_type  = Column(String(20), nullable=False)
    runtime     = Column(Integer, nullable=False)  # minutes; 0 = none, always set by the writer
    fetched_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("tmdb_id", "media_type", name="uq_tmdb_runtime"),
    )
