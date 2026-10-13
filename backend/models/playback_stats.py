from sqlalchemy import (
    JSON, BigInteger, Boolean, Column, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint,
)
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

    # A new row is opened each time an Emby playback restarts after a stop;
    # this groups the rows of one Emby session (``session_key`` stays unique).
    emby_session_key = Column(String(200), nullable=True, index=True)

    # Continuous measurement, in seconds (services.stats_collector._measure).
    # ``watched_seconds`` is this title's real playback; ``exclusive_seconds``
    # is what counts for the user (video only, concurrent devices once).
    watched_seconds   = Column(Integer, nullable=False, default=0, server_default="0")
    exclusive_seconds = Column(Integer, nullable=False, default=0, server_default="0")
    watched_by_hour   = Column(JSON, nullable=True)  # {"YYYY-MM-DDTHH": seconds}, UTC hours
    last_tick_at      = Column(DateTime(timezone=True), nullable=True)
    last_tick_position_ticks = Column(BigInteger, nullable=True)
    # False for rows rebuilt from the pre-measurement history (estimates).
    measured          = Column(Boolean, nullable=False, default=False, server_default="false")
    completed_at      = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_playback_started", "started_at"),
        Index("ix_playback_user_started", "user_id", "started_at"),
        Index("ix_playback_item_started", "item_type", "started_at"),
        Index("ix_playback_library", "library_name", "started_at"),
    )


class PlaybackPauseEvent(Base):
    """One pause/resume cycle observed by the collector.

    A row is created when a session transitions ``playing -> paused`` and
    closed when it transitions back to ``playing`` (the resume tick fills
    ``resumed_at`` and ``duration_seconds``). Open rows (``resumed_at``
    NULL) represent pauses that have not resumed yet — sessions that
    disappear without an explicit resume stay open and never count toward
    the bathroom-break trophy.
    """
    __tablename__ = "playback_pause_events"

    id                = Column(Integer, primary_key=True, index=True)
    session_key       = Column(String(200), nullable=False, index=True)
    emby_session_id   = Column(String(200), nullable=True)
    user_id           = Column(String(100), nullable=False, index=True)
    user_name         = Column(String(200), nullable=False)
    item_id           = Column(String(100), nullable=False, index=True)
    item_name         = Column(String(500), nullable=False)
    item_type         = Column(String(50), nullable=False)

    pause_started_at  = Column(DateTime(timezone=True), nullable=False)
    resumed_at        = Column(DateTime(timezone=True), nullable=True)
    duration_seconds  = Column(Integer, nullable=True)

    created_at        = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("session_key", "pause_started_at", name="uq_pause_session_started"),
        Index("ix_pause_user_started", "user_id", "pause_started_at"),
    )


class PlaybackCompletion(Base):
    """A title counted as watched: its end was reached and enough of its
    runtime was really watched, possibly over several sittings.

    ``source`` is ``live`` when the collector measured it and ``history``
    when it was rebuilt from the estimated pre-measurement sessions.
    """
    __tablename__ = "playback_completions"

    id              = Column(Integer, primary_key=True, index=True)
    session_id      = Column(
        Integer, ForeignKey("playback_sessions.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    user_id         = Column(String(100), nullable=False)
    user_name       = Column(String(200), nullable=False)
    item_id         = Column(String(100), nullable=False)
    item_type       = Column(String(50), nullable=False)
    item_name       = Column(String(500), nullable=False)
    series_name     = Column(String(500), nullable=True)
    season_number   = Column(Integer, nullable=True)
    episode_number  = Column(Integer, nullable=True)
    library_name    = Column(String(200), nullable=True)
    runtime_seconds = Column(Integer, nullable=False)
    watched_seconds = Column(Integer, nullable=False)
    completed_at    = Column(DateTime(timezone=True), nullable=False)
    source          = Column(String(16), nullable=False, default="live", server_default="live")

    __table_args__ = (
        Index("ix_completion_user_item", "user_id", "item_id", "completed_at"),
        Index("ix_completion_completed", "completed_at"),
    )
