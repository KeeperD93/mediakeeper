from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, func
from models.base import Base


class SubtitleProfile(Base):
    """Profil de preferences for les sous-titres."""
    __tablename__ = "subtitle_profiles"

    id               = Column(Integer, primary_key=True, index=True)
    name             = Column(String(100),  nullable=False)
    is_default       = Column(Boolean,      default=False)
    languages        = Column(Text,         nullable=False)   # JSON array: ["fre","eng"]
    include_hi       = Column(Boolean,      default=False)
    include_forced   = Column(Boolean,      default=True)
    exclude_ai       = Column(Boolean,      default=True)
    exclude_machine  = Column(Boolean,      default=True)
    prefer_trusted   = Column(Boolean,      default=True)
    prefer_hash_match = Column(Boolean,     default=True)
    auto_download    = Column(Boolean,      default=False)
    min_score        = Column(Float,        default=3.0)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    updated_at       = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
