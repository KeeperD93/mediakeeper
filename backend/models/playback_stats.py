from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Boolean, Index
from datetime import datetime, timezone
from models.base import Base


class LibraryCache(Base):
    """
    Cache of Emby libraries — refreshed periodically (every hour).
    Avoids re-scanning Emby on every visit to the stats page.
    """
    __tablename__ = "library_cache"

    id            = Column(Integer, primary_key=True, index=True)
    lib_id        = Column(String(100), unique=True, nullable=False, index=True)
    name          = Column(String(300), nullable=False)
    collection_type = Column(String(50), nullable=True)
    total_items   = Column(Integer, default=0)
    count_movies  = Column(Integer, default=0)
    count_series  = Column(Integer, default=0)
    count_seasons = Column(Integer, default=0)
    count_episodes= Column(Integer, default=0)
    size_bytes    = Column(BigInteger, default=0)
    runtime_ticks = Column(BigInteger, default=0)
    updated_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class PlaybackSession(Base):
    """
    Emby playback history — collected periodically.
    Each row = one playback session (start -> stop).
    """
    __tablename__ = "playback_sessions"

    id            = Column(Integer, primary_key=True, index=True)
    session_key   = Column(String(200), unique=True, nullable=False, index=True)  # unique key per session

    user_id       = Column(String(100), nullable=False, index=True)
    user_name     = Column(String(200), nullable=False)
    item_id       = Column(String(100), nullable=False, index=True)
    item_name     = Column(String(500), nullable=False)
    item_type     = Column(String(50), nullable=False)  # Movie, Episode, Audio...
    series_name   = Column(String(500), nullable=True)
    season_number = Column(Integer, nullable=True)
    episode_number= Column(Integer, nullable=True)

    library_name  = Column(String(200), nullable=True)
    client_name   = Column(String(200), nullable=True)
    device_name   = Column(String(200), nullable=True)
    ip_address    = Column(String(100), nullable=True)
    play_method   = Column(String(50), nullable=True)  # DirectPlay, Transcode, DirectStream

    # Container / video / audio streams
    container     = Column(String(50), nullable=True)
    video_codec   = Column(String(50), nullable=True)
    audio_codec   = Column(String(50), nullable=True)
    resolution    = Column(String(20), nullable=True)  # ex: 1080p, 4K
    bitrate       = Column(Integer, nullable=True)      # kbps
    audio_language    = Column(String(50), nullable=True)   # ex: fre, eng, jpn
    subtitle_language = Column(String(50), nullable=True)   # ex: fre, eng
    genres            = Column(String(500), nullable=True)  # ex: "Action,Comedy,Drama"

    # Duration
    duration_ticks  = Column(BigInteger, nullable=True)
    position_ticks  = Column(BigInteger, nullable=True)

    started_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_seen_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    ended_at      = Column(DateTime(timezone=True), nullable=True)
    is_active     = Column(Boolean, default=True)

    __table_args__ = (
        Index("ix_playback_started", "started_at"),
        Index("ix_playback_user_started", "user_id", "started_at"),
        Index("ix_playback_item_started", "item_type", "started_at"),
        Index("ix_playback_library", "library_name", "started_at"),
    )
