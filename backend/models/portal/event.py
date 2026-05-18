from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Boolean, DateTime, ForeignKey, JSON,
    UniqueConstraint,
)
from datetime import datetime, timezone
from models.base import Base


# MediaKeeper Events module — virtual cinema room + invitations.
# Distinct from the legacy SeasonalEvent / WatchParty above. The
# MK* tables back the full event system: private / public events,
# multi-film marathons, invitations with retry limits, virtual
# cinema room, and the universal notification bell.

class MKEvent(Base):
    __tablename__ = "mk_events"

    id              = Column(Integer, primary_key=True, index=True)
    # ``creator_user_id`` becomes nullable + ``ON DELETE SET NULL`` from
    # migration 041. The GDPR purge auto-cancels every still-scheduled
    # event of the leaving user before the FK kicks in, so SET NULL only
    # applies to ``done`` / ``cancelled`` events that retain historical
    # value (achievements, statistics).
    creator_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"),
                             nullable=True, index=True)
    title           = Column(String(200), nullable=False)
    # 'private' or 'public'
    kind            = Column(String(20), nullable=False, server_default="private")
    # JSON list of media items in viewing order:
    # [{tmdb_id, media_type, title, poster_url, runtime_min}]
    # A single item = a regular event, multiple = a marathon.
    tmdb_ids        = Column(JSON, nullable=False)
    scheduled_at    = Column(DateTime(timezone=True), nullable=False, index=True)
    comment         = Column(Text, nullable=True)
    # 'scheduled' | 'cancelled' | 'done'
    status          = Column(String(20), nullable=False,
                             server_default="scheduled", index=True)
    room_opened_at  = Column(DateTime(timezone=True), nullable=True)
    # Server-authoritative marathon index. Bumped via the /advance
    # endpoint once every accepted participant in the room has crossed
    # the 85% threshold for ``tmdb_ids[current_step]``.
    current_step    = Column(Integer, nullable=False, server_default="0")
    created_at      = Column(DateTime(timezone=True),
                             default=lambda: datetime.now(timezone.utc))
    updated_at      = Column(DateTime(timezone=True),
                             default=lambda: datetime.now(timezone.utc),
                             onupdate=lambda: datetime.now(timezone.utc))


class MKEventInvitation(Base):
    __tablename__ = "mk_event_invitations"
    __table_args__ = (
        UniqueConstraint("event_id", "user_id", name="uq_mk_event_invitation"),
    )

    id            = Column(Integer, primary_key=True, index=True)
    event_id      = Column(Integer, ForeignKey("mk_events.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    user_id       = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    # 'pending' | 'accepted' | 'declined' | 'removed'
    status        = Column(String(20), nullable=False, server_default="pending")
    # How many times the creator has invited this user. Capped at 3
    # for private events; ignored for public events (auto-included).
    invite_count  = Column(Integer, nullable=False, server_default="1")
    # Seat assigned at room entry (0..19), null until then.
    seat_index    = Column(Integer, nullable=True)
    # Per-user marathon step: each participant can be on a different
    # film. Latecomers and viewers who fall behind keep watching their
    # current step while peers advance. The legacy ``MKEvent.current_step``
    # is kept as the "max step reached by the group" for the readiness
    # gate / event-wide signals (see migration 051).
    user_step     = Column(Integer, nullable=False, server_default="0")
    # Heartbeat from the open cinema-room tab. ``None`` means the user
    # has never entered (or left and let the heartbeat lapse): seats
    # still resolve via ``seat_index`` so a returning viewer takes back
    # the same seat, but the live UI hides their avatar until the
    # heartbeat reports them online again (see migration 051).
    last_seen_at  = Column(DateTime(timezone=True), nullable=True)
    invited_at    = Column(DateTime(timezone=True),
                           default=lambda: datetime.now(timezone.utc))
    responded_at  = Column(DateTime(timezone=True), nullable=True)


class MKEventMessage(Base):
    __tablename__ = "mk_event_messages"

    id        = Column(BigInteger().with_variant(Integer, "sqlite"),
                       primary_key=True, index=True)
    event_id  = Column(Integer, ForeignKey("mk_events.id", ondelete="CASCADE"),
                       nullable=False, index=True)
    # Mirrors ``chat_messages.user_id`` — anonymised on author purge so
    # the surrounding event-room conversation remains coherent for the
    # other participants. Migration 041.
    user_id   = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"),
                       nullable=True)
    content   = Column(String(2000), nullable=False)
    sent_at   = Column(DateTime(timezone=True),
                       default=lambda: datetime.now(timezone.utc), index=True)


class MKNotification(Base):
    """
    Universal bell for the Requests module. Not only for events:
    future notifications such as request_approved, request_rejected, ticket_replied
    will also flow through here.
    """
    __tablename__ = "mk_notifications"

    # BigInteger everywhere except SQLite (test suite) where plain INTEGER is
    # required for PK autoincrement to kick in.
    id          = Column(BigInteger().with_variant(Integer, "sqlite"),
                         primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    type        = Column(String(50), nullable=False)
    payload     = Column(JSON, nullable=True)
    read        = Column(Boolean, nullable=False, server_default="false", index=True)
    created_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc), index=True)


class SeasonalEvent(Base):
    __tablename__ = "seasonal_events"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String(200), nullable=False)
    description   = Column(Text, nullable=True)
    start_date    = Column(DateTime(timezone=True), nullable=False)
    end_date      = Column(DateTime(timezone=True), nullable=False)
    genre_filter  = Column(JSON, nullable=True)
    target_count  = Column(Integer, server_default="10", nullable=False)
    badge_id      = Column(String(50), ForeignKey("achievements.id",
                           ondelete="SET NULL"), nullable=True)
    created_by    = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"),
                           nullable=True)
    created_at    = Column(DateTime(timezone=True),
                           default=lambda: datetime.now(timezone.utc))


class SeasonalProgress(Base):
    __tablename__ = "seasonal_progress"
    __table_args__ = (
        UniqueConstraint("event_id", "user_id", name="uq_seasonal_progress"),
    )

    id          = Column(Integer, primary_key=True, index=True)
    event_id    = Column(Integer, ForeignKey("seasonal_events.id",
                         ondelete="CASCADE"), nullable=False, index=True)
    user_id     = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    progress    = Column(Integer, server_default="0", nullable=False)
    completed   = Column(Boolean, server_default="false", nullable=False)


class WatchParty(Base):
    __tablename__ = "watch_parties"

    id                = Column(Integer, primary_key=True, index=True)
    # Legacy parallel to ``MKEvent``. ``host_user_id`` becomes nullable
    # + ``ON DELETE SET NULL`` from migration 041 — kept consistent with
    # the rest of the consumer-side FK policy.
    host_user_id      = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"),
                               nullable=True, index=True)
    title             = Column(String(300), nullable=False)
    tmdb_id           = Column(Integer, nullable=True)
    media_type        = Column(String(20), nullable=True)
    scheduled_at      = Column(DateTime(timezone=True), nullable=False)
    max_participants  = Column(Integer, server_default="20", nullable=False)
    chat_room_id      = Column(Integer, ForeignKey("chat_rooms.id",
                               ondelete="SET NULL"), nullable=True)
    created_at        = Column(DateTime(timezone=True),
                               default=lambda: datetime.now(timezone.utc))


class WatchPartyParticipant(Base):
    __tablename__ = "watch_party_participants"
    __table_args__ = (
        UniqueConstraint("party_id", "user_id", name="uq_party_participant"),
    )

    id        = Column(Integer, primary_key=True, index=True)
    party_id  = Column(Integer, ForeignKey("watch_parties.id", ondelete="CASCADE"),
                       nullable=False, index=True)
    user_id   = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                       nullable=False)
    joined_at = Column(DateTime(timezone=True),
                       default=lambda: datetime.now(timezone.utc))
