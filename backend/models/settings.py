from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime, timezone
from models.base import Base


class Setting(Base):
    """
    Table cle/value for la configuration des outils.
    Each outil a several entrees : url, api_key, enabled.
    Ex: key="emby.url", value="http://192.168.1.x:8096"
        key="emby.enabled", value="true"
    """
    __tablename__ = "settings"

    id         = Column(Integer, primary_key=True, index=True)
    key        = Column(String(100), unique=True, nullable=False, index=True)
    value      = Column(Text, nullable=True, default="")
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
