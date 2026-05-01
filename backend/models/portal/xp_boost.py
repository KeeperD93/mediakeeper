"""XP Boost Event model — admin-defined date ranges with XP multipliers.

Used to run themed XP campaigns (Christmas double-XP, Halloween triple-XP, etc.).
Multiple events can be active at the same time; they multiply together.
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, func
from models.base import Base


class XpBoostEvent(Base):
    __tablename__ = "xp_boost_events"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    multiplier = Column(Float, nullable=False, default=2.0)
    starts_at = Column(DateTime(timezone=True), nullable=False)
    ends_at = Column(DateTime(timezone=True), nullable=False)
    # Optional comma-separated action filter (e.g. "achievement_unlocked,watch_movie").
    # Empty / NULL means "applies to all actions".
    action_filter = Column(String(500), nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
