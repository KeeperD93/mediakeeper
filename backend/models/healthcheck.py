from sqlalchemy import Column, Integer, String, Text, DateTime, Index  # noqa: F401
from datetime import datetime, timezone
from models.base import Base


class HealthCheckResult(Base):
    """Result of a health scan for a media item."""
    __tablename__ = "healthcheck_results"

    id          = Column(Integer, primary_key=True, index=True)
    item_id     = Column(String(100), nullable=False, index=True)
    item_name   = Column(String(500), nullable=False)
    item_type   = Column(String(50), nullable=False)       # Movie, Episode
    series_id   = Column(String(100), nullable=True, index=True)
    series_name = Column(String(500), nullable=True)
    season_num  = Column(Integer, nullable=True)
    episode_num = Column(Integer, nullable=True)
    library_name = Column(String(200), nullable=True)
    issues      = Column(Text, nullable=False, default="[]")  # JSON array of issue objects
    severity    = Column(String(20), nullable=False, default="info")  # critical, warning, info
    file_path   = Column(String(2000), nullable=True)
    scanned_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_hc_library", "library_name"),
        Index("ix_hc_severity", "severity"),
        Index("ix_hc_scanned", "scanned_at"),
    )
