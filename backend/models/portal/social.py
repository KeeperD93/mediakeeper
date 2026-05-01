from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON,
    UniqueConstraint, false,
)
from datetime import datetime, timezone
from models.base import Base


# Three-tier privacy model for user lists.
PRIVACY_PRIVATE = "private"
PRIVACY_PUBLIC_READONLY = "public_readonly"
PRIVACY_COLLABORATIVE = "collaborative"
VALID_PRIVACY = {PRIVACY_PRIVATE, PRIVACY_PUBLIC_READONLY, PRIVACY_COLLABORATIVE}

VALID_CONTENT_TYPES = {"movies", "series", "documentaries", "mixed"}


class UserList(Base):
    __tablename__ = "user_lists"

    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    name          = Column(String(200), nullable=False)
    description   = Column(Text, nullable=True)
    privacy       = Column(String(20), server_default=PRIVACY_PRIVATE,
                           nullable=False, index=True)
    content_type  = Column(String(20), server_default="mixed", nullable=False)
    genres        = Column(JSON, nullable=True)
    sort_order    = Column(Integer, server_default="0", nullable=False)
    copy_count    = Column(Integer, server_default="0", nullable=False)
    owner_muted   = Column(Boolean, default=False, server_default=false(), nullable=False)
    is_deleted    = Column(Boolean, default=False, server_default=false(),
                           nullable=False, index=True)
    deleted_at    = Column(DateTime(timezone=True), nullable=True)
    created_at    = Column(DateTime(timezone=True),
                           default=lambda: datetime.now(timezone.utc))
    updated_at    = Column(DateTime(timezone=True),
                           default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))


class UserListItem(Base):
    __tablename__ = "user_list_items"
    __table_args__ = (
        UniqueConstraint("list_id", "tmdb_id", "media_type",
                         name="uq_list_item"),
    )

    id                = Column(Integer, primary_key=True, index=True)
    list_id           = Column(Integer, ForeignKey("user_lists.id",
                               ondelete="CASCADE"), nullable=False, index=True)
    tmdb_id           = Column(Integer, nullable=False)
    media_type        = Column(String(20), nullable=False)
    # Snapshot of TMDB metadata at add-time so the list can render
    # title + poster without a lookup. Nullable for legacy rows.
    title             = Column(String(500), nullable=True)
    poster_url        = Column(String(500), nullable=True)
    year              = Column(Integer, nullable=True)
    added_by_user_id  = Column(Integer, ForeignKey("users.id",
                               ondelete="SET NULL"), nullable=True)
    added_at          = Column(DateTime(timezone=True),
                               default=lambda: datetime.now(timezone.utc))


class UserListContributor(Base):
    """Explicit contributor on a collaborative list. The owner is always
    implicitly authorised and never appears in this table."""
    __tablename__ = "user_list_contributors"
    __table_args__ = (
        UniqueConstraint("list_id", "user_id", name="uq_list_contributor"),
    )

    id          = Column(Integer, primary_key=True, index=True)
    list_id     = Column(Integer, ForeignKey("user_lists.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    user_id     = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    muted       = Column(Boolean, default=False, server_default=false(), nullable=False)
    added_at    = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc))


class UserListHistory(Base):
    """Audit log for lists — one row per edit on public/collaborative lists.

    Feeds both the user-facing history column and the admin undo action.
    For private lists we still log creation + deletion so admins can undo."""
    __tablename__ = "user_list_history"

    id           = Column(Integer, primary_key=True, index=True)
    list_id      = Column(Integer, ForeignKey("user_lists.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    user_id      = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"),
                          nullable=True)
    action       = Column(String(30), nullable=False, index=True)
    tmdb_id      = Column(Integer, nullable=True)
    media_type   = Column(String(20), nullable=True)
    title        = Column(String(500), nullable=True)
    extra        = Column(JSON, nullable=True)
    created_at   = Column(DateTime(timezone=True),
                          default=lambda: datetime.now(timezone.utc),
                          index=True)


class UserRating(Base):
    __tablename__ = "user_ratings"
    __table_args__ = (
        UniqueConstraint("user_id", "tmdb_id", "media_type",
                         name="uq_user_rating"),
    )

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    tmdb_id     = Column(Integer, nullable=False, index=True)
    media_type  = Column(String(20), nullable=False)
    rating      = Column(Integer, nullable=False)
    review      = Column(Text, nullable=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc))


class UserRatingLike(Base):
    __tablename__ = "user_rating_likes"
    __table_args__ = (
        UniqueConstraint("rating_id", "user_id", name="uq_rating_like"),
    )

    id          = Column(Integer, primary_key=True, index=True)
    rating_id   = Column(Integer, ForeignKey("user_ratings.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    user_id     = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                         nullable=False)


class ReleaseReminder(Base):
    __tablename__ = "release_reminders"
    __table_args__ = (
        UniqueConstraint("user_id", "tmdb_id", "media_type",
                         name="uq_release_reminder"),
    )

    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    tmdb_id       = Column(Integer, nullable=False)
    media_type    = Column(String(20), nullable=False)
    release_date  = Column(DateTime(timezone=True), nullable=True)
    notified      = Column(Boolean, default=False, server_default=false(), nullable=False)
