from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime, timezone
from models.base import Base


class NotificationChannel(Base):
    """
    Notification channel configuration.
    Replaces the settings keys `notifications.discord`, `notifications.imgur`, `notifications.queue`.
    Each row = one channel or one notification payload (keyed by `channel_key`).
    """
    __tablename__ = "notification_channels"

    id           = Column(Integer, primary_key=True, index=True)
    channel_key  = Column(String(200), unique=True, nullable=False, index=True)
    # Ex: "discord", "imgur", "queue"
    data         = Column(Text, nullable=True, default="{}")
    updated_at   = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
