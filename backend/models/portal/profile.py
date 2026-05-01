from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON,
)
from datetime import datetime, timezone
from models.base import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                             unique=True, nullable=False, index=True)
    display_name    = Column(String(50), nullable=False)
    avatar_url      = Column(String(500), nullable=True)
    avatar_custom_path = Column(String(500), nullable=True)
    bio             = Column(Text, nullable=True)
    display_name_must_set = Column(Boolean, server_default="true", nullable=False)
    display_name_changed_at = Column(DateTime(timezone=True), nullable=True)
    favorite_genres = Column(JSON, nullable=True)
    level           = Column(Integer, server_default="1", nullable=False)
    xp              = Column(Integer, server_default="0", nullable=False)
    selected_badges = Column(JSON, nullable=True)
    selected_title  = Column(String(100), nullable=True)
    avatar_effect   = Column(String(50), nullable=True)
    is_public       = Column(Boolean, server_default="true", nullable=False)
    role            = Column(String(20), server_default="viewer", nullable=False)
    language        = Column(String(10), server_default="fr", nullable=False)
    chat_enabled    = Column(Boolean, server_default="true", nullable=False)
    chat_muted_until = Column(DateTime(timezone=True), nullable=True)
    chat_last_read_message_id = Column(Integer, nullable=True)
    hide_adult      = Column(Boolean, server_default="true", nullable=False)
    account_active  = Column(Boolean, server_default="true", nullable=False)
    forced_public   = Column(Boolean, nullable=True)

    # Premium user management (migration 035)
    source          = Column(String(20), server_default="emby", nullable=False)
    emby_user_id    = Column(String(64), nullable=True, index=True)
    first_name      = Column(String(100), nullable=True)
    last_name       = Column(String(100), nullable=True)
    email           = Column(String(255), nullable=True)
    access_start_date = Column(DateTime(timezone=True), nullable=True)
    access_end_date = Column(DateTime(timezone=True), nullable=True)
    last_seen_at    = Column(DateTime(timezone=True), nullable=True)
    last_login_at   = Column(DateTime(timezone=True), nullable=True)
    last_login_ip   = Column(String(64), nullable=True)
    last_login_user_agent = Column(String(255), nullable=True)
    admin_notes     = Column(Text, nullable=True)
    tags            = Column(JSON, nullable=True)
    can_chat        = Column(Boolean, server_default="true", nullable=False)
    can_portal      = Column(Boolean, server_default="true", nullable=False)
    can_problems    = Column(Boolean, server_default="true", nullable=False)
    can_lists       = Column(Boolean, server_default="true", nullable=False)
    can_earn_xp_offline = Column(Boolean, server_default="false", nullable=False)
    emby_is_disabled = Column(Boolean, nullable=True)
    tokens_invalidated_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at      = Column(DateTime(timezone=True), nullable=True, index=True)
    deleted_by_user_id = Column(Integer, nullable=True)

    created_at      = Column(DateTime(timezone=True),
                             default=lambda: datetime.now(timezone.utc))
    updated_at      = Column(DateTime(timezone=True),
                             default=lambda: datetime.now(timezone.utc),
                             onupdate=lambda: datetime.now(timezone.utc))
