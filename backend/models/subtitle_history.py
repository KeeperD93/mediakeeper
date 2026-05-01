from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, func
from models.base import Base


class SubtitleDownload(Base):
    """History des sous-titres telecharges."""
    __tablename__ = "subtitle_downloads"

    id              = Column(Integer, primary_key=True, index=True)
    emby_item_id    = Column(String(64),   nullable=False, index=True)
    media_name      = Column(String(500),  nullable=False)
    media_type      = Column(String(20),   nullable=True)   # Movie | Episode
    series_name     = Column(String(300),  nullable=True)
    season          = Column(Integer,      nullable=True)
    episode         = Column(Integer,      nullable=True)
    os_file_id      = Column(Integer,      nullable=False)
    os_subtitle_id  = Column(String(50),   nullable=True)
    file_name       = Column(String(500),  nullable=True)
    language        = Column(String(10),   nullable=False, index=True)
    destination     = Column(String(1000), nullable=False)
    file_size       = Column(Integer,      nullable=True)
    quality_score   = Column(Float,        nullable=True)
    hash_match      = Column(Boolean,      default=False)
    hearing_impaired = Column(Boolean,     default=False)
    foreign_parts_only = Column(Boolean,   default=False)
    from_trusted    = Column(Boolean,      default=False)
    ai_translated   = Column(Boolean,      default=False)
    source          = Column(String(50),   default="opensubtitles")
    downloaded_at   = Column(DateTime(timezone=True), server_default=func.now())
