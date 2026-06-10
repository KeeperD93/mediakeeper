from sqlalchemy import Column, Integer, ForeignKey, Text, DateTime
from datetime import datetime, timezone
from models.base import Base


class UserPreference(Base):
    """
    User preferences: theme, sidebar, language, timezone, dashboard layout.
    One row per user.
    Replaces the settings keys `user.{id}.preferences` and `user.{id}.dashboard.layout`.
    """
    __tablename__ = "user_preferences"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    # JSON : {"theme": "dark", "sidebar_collapsed": false, "language": "fr", "timezone": "Europe/Paris"}
    preferences = Column(Text, nullable=True, default="{}")
    # JSON : {"hidden": [], "positions": {...}}
    dashboard_layout = Column(Text, nullable=True, default="{}")
    # JSON : {"stats.activity": [w0, w1, ...]} — resizable table column widths, per table id.
    table_columns = Column(Text, nullable=True, default="{}")
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
