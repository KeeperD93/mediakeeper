from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime, timezone
from models.base import Base


class NotificationLog(Base):
    """Log of every notification sent."""
    __tablename__ = "notification_logs"

    id          = Column(Integer, primary_key=True, index=True)
    event_type  = Column(String(100), nullable=False, index=True)  # added, offline, duplicate...
    channel     = Column(String(50), default="discord")  # discord, telegram, email
    webhook_name= Column(String(200), nullable=True)
    title       = Column(String(500), nullable=True)
    message     = Column(Text, nullable=True)
    status      = Column(String(20), default="sent")  # sent, failed, queued, grouped
    error       = Column(Text, nullable=True)
    sent_at     = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
