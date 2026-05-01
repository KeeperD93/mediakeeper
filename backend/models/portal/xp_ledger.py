"""XP Ledger model — tracks every XP grant for audit + anti-abuse."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, func
from models.base import Base


class XpLedger(Base):
    __tablename__ = "xp_ledger"
    __table_args__ = (
        UniqueConstraint("user_id", "action", "reference", name="uq_xp_user_action_ref"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    reference = Column(String(200), nullable=False)
    xp = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
