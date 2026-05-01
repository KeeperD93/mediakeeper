from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime, timezone
from models.base import Base


class WatchlistScan(Base):
    """
    Storage for watchlist data: scan_results, tracked, ignored, calendar cache.
    Replaces the settings keys `watchlist.*`.
    Each row = one data category (keyed by `scan_key`).
    The `data` field holds the JSON with a mandatory `schema_version`.
    """
    __tablename__ = "watchlist_scans"

    id          = Column(Integer, primary_key=True, index=True)
    scan_key    = Column(String(200), unique=True, nullable=False, index=True)
    # Ex: "scan_results", "tracked", "ignored", "calendar.2026-03"
    data        = Column(Text, nullable=True, default="{}")
    # schema_version is tracked inside the `data` JSON itself
    updated_at  = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
