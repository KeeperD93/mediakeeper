"""Continuous watch-time measurement + watched titles

The collector now measures real playback at every poll (pauses, seeks and
silent players add nothing) and records titles counted as watched. Sessions
recorded before this change are backfilled once with the best available
estimate: the smallest positive of wall clock, reached position and runtime,
so a session never counts more than its own title. That time is spread over
the hours following the start, and a title whose end was reached with enough
estimated watching becomes a ``history`` completion. Music is kept per title
but never counts as the user's watch time.

Revision ID: 062_continuous_watch_measurement
Revises: 061_feedback_reports
Create Date: 2026-10-13
"""
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from alembic import op

revision = "062_continuous_watch_measurement"
down_revision = "061_feedback_reports"
branch_labels = None
depends_on = None

_TICKS_PER_SECOND = 10_000_000
_END_RATIO = 0.85
_WATCHED_RATIO = 0.75
_COMPLETION_WINDOW = timedelta(days=30)
_VIDEO_TYPES = ("Movie", "Episode")
_BATCH = 500

_SESSIONS = sa.table(
    "playback_sessions",
    sa.column("id", sa.Integer),
    sa.column("session_key", sa.String),
    sa.column("emby_session_key", sa.String),
    sa.column("user_id", sa.String),
    sa.column("user_name", sa.String),
    sa.column("item_id", sa.String),
    sa.column("item_type", sa.String),
    sa.column("item_name", sa.String),
    sa.column("series_name", sa.String),
    sa.column("season_number", sa.Integer),
    sa.column("episode_number", sa.Integer),
    sa.column("library_name", sa.String),
    sa.column("duration_ticks", sa.BigInteger),
    sa.column("position_ticks", sa.BigInteger),
    sa.column("started_at", sa.DateTime(timezone=True)),
    sa.column("last_seen_at", sa.DateTime(timezone=True)),
    sa.column("ended_at", sa.DateTime(timezone=True)),
    sa.column("watched_seconds", sa.Integer),
    sa.column("exclusive_seconds", sa.Integer),
    sa.column("watched_by_hour", sa.JSON),
    sa.column("completed_at", sa.DateTime(timezone=True)),
)
_COMPLETIONS = sa.table(
    "playback_completions",
    sa.column("session_id", sa.Integer),
    sa.column("user_id", sa.String),
    sa.column("user_name", sa.String),
    sa.column("item_id", sa.String),
    sa.column("item_type", sa.String),
    sa.column("item_name", sa.String),
    sa.column("series_name", sa.String),
    sa.column("season_number", sa.Integer),
    sa.column("episode_number", sa.Integer),
    sa.column("library_name", sa.String),
    sa.column("runtime_seconds", sa.Integer),
    sa.column("watched_seconds", sa.Integer),
    sa.column("completed_at", sa.DateTime(timezone=True)),
    sa.column("source", sa.String),
)


def _new_columns() -> list[sa.Column]:
    # Fresh Column objects on every call: a Column can only belong to one table.
    return [
        sa.Column("emby_session_key", sa.String(length=200), nullable=True),
        sa.Column("watched_seconds", sa.Integer(), server_default="0", nullable=False),
        sa.Column("exclusive_seconds", sa.Integer(), server_default="0", nullable=False),
        sa.Column("watched_by_hour", sa.JSON(), nullable=True),
        sa.Column("last_tick_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_tick_position_ticks", sa.BigInteger(), nullable=True),
        sa.Column("measured", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    ]


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _estimate_seconds(row) -> int:
    started = _utc(row.started_at)
    ended = _utc(row.ended_at) or _utc(row.last_seen_at)
    wall = (ended - started).total_seconds() if started and ended and ended >= started else 0
    position = (row.position_ticks or 0) / _TICKS_PER_SECOND
    runtime = (row.duration_ticks or 0) / _TICKS_PER_SECOND
    candidates = [c for c in (wall, position, runtime) if c > 0]
    return int(min(candidates)) if candidates else 0


def _spread_over_hours(start: datetime, seconds: int) -> dict[str, int]:
    """Lay ``seconds`` of watching contiguously from ``start``, per UTC hour."""
    buckets: dict[str, int] = {}
    cursor, left = start, seconds
    while left > 0:
        next_hour = cursor.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        chunk = min(left, int((next_hour - cursor).total_seconds()) or 1)
        key = cursor.strftime("%Y-%m-%dT%H")
        buckets[key] = buckets.get(key, 0) + chunk
        left -= chunk
        cursor = next_hour
    return buckets


def _completions_for(rows: list, watched: dict[int, int]) -> list[tuple]:
    """Replay one user's sittings of one title: (row, cumulative seconds) per completion."""
    found, sittings = [], []
    for row in rows:
        runtime = (row.duration_ticks or 0) / _TICKS_PER_SECOND
        started = _utc(row.started_at)
        if runtime <= 0 or started is None:
            continue
        sittings = [(s, w) for s, w in sittings if s >= started - _COMPLETION_WINDOW]
        sittings.append((started, watched[row.id]))
        reached_end = (row.position_ticks or 0) / _TICKS_PER_SECOND >= runtime * _END_RATIO
        total = sum(w for _, w in sittings)
        if reached_end and total >= runtime * _WATCHED_RATIO:
            found.append((row, total, int(runtime)))
            sittings = []
    return found


def _backfill(bind) -> None:
    rows = bind.execute(
        sa.select(_SESSIONS).where(_SESSIONS.c.emby_session_key.is_(None)).order_by(_SESSIONS.c.started_at)
    ).all()
    if not rows:
        return

    watched: dict[int, int] = {}
    updates = []
    by_title: dict[tuple, list] = defaultdict(list)
    for row in rows:
        seconds = _estimate_seconds(row)
        watched[row.id] = seconds
        is_video = row.item_type in _VIDEO_TYPES
        started = _utc(row.started_at)
        updates.append({
            "_id": row.id,
            "_key": row.session_key,
            "_watched": seconds,
            "_exclusive": seconds if is_video else 0,
            "_hours": _spread_over_hours(started, seconds) if is_video and started and seconds else None,
            "_completed": None,
        })
        if is_video:
            by_title[(row.user_id, row.item_id)].append(row)

    completions, completed_ids = [], {}
    for title_rows in by_title.values():
        for row, total, runtime in _completions_for(title_rows, watched):
            done_at = _utc(row.ended_at) or _utc(row.last_seen_at) or _utc(row.started_at)
            completed_ids[row.id] = done_at
            completions.append({
                "session_id": row.id, "user_id": row.user_id, "user_name": row.user_name,
                "item_id": row.item_id, "item_type": row.item_type, "item_name": row.item_name,
                "series_name": row.series_name, "season_number": row.season_number,
                "episode_number": row.episode_number, "library_name": row.library_name,
                "runtime_seconds": runtime, "watched_seconds": int(total),
                "completed_at": done_at, "source": "history",
            })
    for update in updates:
        update["_completed"] = completed_ids.get(update["_id"])

    statement = (
        sa.update(_SESSIONS)
        .where(_SESSIONS.c.id == sa.bindparam("_id"))
        .values(
            emby_session_key=sa.bindparam("_key"),
            watched_seconds=sa.bindparam("_watched"),
            exclusive_seconds=sa.bindparam("_exclusive"),
            watched_by_hour=sa.bindparam("_hours", type_=sa.JSON),
            completed_at=sa.bindparam("_completed", type_=sa.DateTime(timezone=True)),
        )
    )
    for i in range(0, len(updates), _BATCH):
        bind.execute(statement, updates[i:i + _BATCH])
    for i in range(0, len(completions), _BATCH):
        bind.execute(sa.insert(_COMPLETIONS), completions[i:i + _BATCH])


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing = {c["name"] for c in inspector.get_columns("playback_sessions")}
    for column in _new_columns():
        if column.name not in existing:
            op.add_column("playback_sessions", column)
    if "ix_playback_sessions_emby_session_key" not in {
        i["name"] for i in inspector.get_indexes("playback_sessions")
    }:
        op.create_index(
            "ix_playback_sessions_emby_session_key", "playback_sessions", ["emby_session_key"]
        )

    if "playback_completions" not in set(inspector.get_table_names()):
        op.create_table(
            "playback_completions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "session_id",
                sa.Integer(),
                sa.ForeignKey("playback_sessions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("user_id", sa.String(length=100), nullable=False),
            sa.Column("user_name", sa.String(length=200), nullable=False),
            sa.Column("item_id", sa.String(length=100), nullable=False),
            sa.Column("item_type", sa.String(length=50), nullable=False),
            sa.Column("item_name", sa.String(length=500), nullable=False),
            sa.Column("series_name", sa.String(length=500), nullable=True),
            sa.Column("season_number", sa.Integer(), nullable=True),
            sa.Column("episode_number", sa.Integer(), nullable=True),
            sa.Column("library_name", sa.String(length=200), nullable=True),
            sa.Column("runtime_seconds", sa.Integer(), nullable=False),
            sa.Column("watched_seconds", sa.Integer(), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("source", sa.String(length=16), server_default="live", nullable=False),
        )
        op.create_index("ix_playback_completions_id", "playback_completions", ["id"])
        op.create_index("ix_playback_completions_session_id", "playback_completions", ["session_id"])
        op.create_index(
            "ix_completion_user_item", "playback_completions", ["user_id", "item_id", "completed_at"]
        )
        op.create_index("ix_completion_completed", "playback_completions", ["completed_at"])

    _backfill(bind)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "playback_completions" in set(inspector.get_table_names()):
        op.drop_table("playback_completions")
    if "ix_playback_sessions_emby_session_key" in {
        i["name"] for i in inspector.get_indexes("playback_sessions")
    }:
        op.drop_index("ix_playback_sessions_emby_session_key", table_name="playback_sessions")
    existing = {c["name"] for c in inspector.get_columns("playback_sessions")}
    for column in _new_columns():
        if column.name in existing:
            op.drop_column("playback_sessions", column.name)
