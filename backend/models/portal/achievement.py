from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, Index,
)
from models.base import Base


class Achievement(Base):
    __tablename__ = "achievements"

    id              = Column(String(50), primary_key=True)
    category        = Column(String(30), nullable=False, index=True)
    name_key        = Column(String(100), nullable=False)
    description_key = Column(String(100), nullable=False)
    icon            = Column(String(100), nullable=False)
    tier            = Column(Integer, server_default="1", nullable=False)
    xp_reward       = Column(Integer, server_default="10", nullable=False)
    threshold       = Column(Integer, server_default="1", nullable=False)
    condition_type  = Column(String(50), nullable=False)
    next_tier_id    = Column(String(50), ForeignKey("achievements.id",
                             ondelete="SET NULL"), nullable=True)
    secret          = Column(Boolean, server_default="false", nullable=False)
    sort_order      = Column(Integer, server_default="0", nullable=False)


class UserAchievement(Base):
    __tablename__ = "user_achievements"
    __table_args__ = (
        Index(
            "uq_user_achievements_user_achievement",
            "user_id",
            "achievement_id",
            unique=True,
        ),
    )

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    achievement_id  = Column(String(50), ForeignKey("achievements.id",
                             ondelete="CASCADE"), nullable=False, index=True)
    progress        = Column(Integer, server_default="0", nullable=False)
    unlocked        = Column(Boolean, server_default="false", nullable=False)
    unlocked_at     = Column(DateTime(timezone=True), nullable=True)
    notified        = Column(Boolean, server_default="false", nullable=False)
