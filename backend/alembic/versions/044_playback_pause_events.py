"""Add ``playback_pause_events`` table for the bathroom-break trophy.

The collector observes Emby ``/Sessions`` every ~15s. To unlock
``secret_pipi`` (5 short pauses between 2 and 5 minutes) we need a
durable record of each pause/resume cycle, so a new table is added:

* ``session_key`` matches the format used by ``playback_sessions``
  (`<emby_user_id>_<emby_item_id>_<session_id>`).
* ``pause_started_at`` is filled when a tick reports ``IsPaused=True``
  and no open pause exists yet for that ``session_key``.
* ``resumed_at`` + ``duration_seconds`` are filled when the next tick
  reports ``IsPaused=False`` (the pause closes).
* Open rows (no ``resumed_at``) survive across restarts; sessions that
  disappear without resuming explicitly never become qualifying events.

The unique constraint ``(session_key, pause_started_at)`` deduplicates
re-emitted pause ticks when the same paused session is observed twice in
a row by the collector.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "044_playback_pause_events"
down_revision: Union[str, None] = "043_emby_tmdb_index_date_created"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "playback_pause_events" not in existing_tables:
        op.create_table(
            "playback_pause_events",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("session_key", sa.String(length=200), nullable=False),
            sa.Column("emby_session_id", sa.String(length=200), nullable=True),
            sa.Column("user_id", sa.String(length=100), nullable=False),
            sa.Column("user_name", sa.String(length=200), nullable=False),
            sa.Column("item_id", sa.String(length=100), nullable=False),
            sa.Column("item_name", sa.String(length=500), nullable=False),
            sa.Column("item_type", sa.String(length=50), nullable=False),
            sa.Column("pause_started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("resumed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("duration_seconds", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint(
                "session_key", "pause_started_at",
                name="uq_pause_session_started",
            ),
        )
        op.create_index(
            "ix_playback_pause_events_session_key",
            "playback_pause_events", ["session_key"],
        )
        op.create_index(
            "ix_playback_pause_events_user_id",
            "playback_pause_events", ["user_id"],
        )
        op.create_index(
            "ix_playback_pause_events_item_id",
            "playback_pause_events", ["item_id"],
        )
        op.create_index(
            "ix_pause_user_started",
            "playback_pause_events", ["user_id", "pause_started_at"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "playback_pause_events" in existing_tables:
        op.drop_index(
            "ix_pause_user_started",
            table_name="playback_pause_events",
        )
        op.drop_index(
            "ix_playback_pause_events_item_id",
            table_name="playback_pause_events",
        )
        op.drop_index(
            "ix_playback_pause_events_user_id",
            table_name="playback_pause_events",
        )
        op.drop_index(
            "ix_playback_pause_events_session_key",
            table_name="playback_pause_events",
        )
        op.drop_table("playback_pause_events")
