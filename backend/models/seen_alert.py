from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from datetime import datetime, timezone
from models.base import Base


class SeenAlert(Base):
    """
    Stocke les alertes Emby marquees 'Lu' par user.
    alert_id = identifiant unique de l'alerte (id ou date from Emby)
    """
    __tablename__ = "seen_alerts"

    id       = Column(Integer, primary_key=True, index=True)
    user_id  = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    alert_id = Column(String(255), nullable=False)
    seen_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
