"""Time watched alone, kept on each watched title

A title counts as watched on the time of its own playback rows, but a user
playing two titles at once is credited once per poll: only the row that moved
most gets that time (``playback_sessions.exclusive_seconds``). Watch XP needs
that share as it was when the title counted as watched, which nothing kept:
``playback_completions.exclusive_seconds`` now does.

Backfilled once:
- ``history`` completions: 062 set the exclusive time of a rebuilt row to its
  estimate, so the share equals ``watched_seconds``;
- ``live`` completions: the exclusive seconds of the user's sittings of the
  same title, from the previous completion of that title (or 30 days back) up
  to the completion, plus its own row, as the collector adds them up. A row
  keeps counting after its title is watched (end credits): the last sitting is
  slightly overstated.

Revision ID: 070_completion_exclusive_seconds
Revises: 069_profile_level_floor
Create Date: 2026-11-12
"""
from collections import defaultdict
from datetime import UTC, datetime, timedelta

import sqlalchemy as sa
from alembic import op

revision = "070_completion_exclusive_seconds"
down_revision = "069_profile_level_floor"
branch_labels = None
depends_on = None

_TABLE = "playback_completions"
_COLUMN = "exclusive_seconds"
_COMPLETION_WINDOW = timedelta(days=30)
_BATCH = 500

_SESSIONS = sa.table(
    "playback_sessions",
    sa.column("id", sa.Integer),
    sa.column("user_id", sa.String),
    sa.column("item_id", sa.String),
    sa.column("started_at", sa.DateTime(timezone=True)),
    sa.column("exclusive_seconds", sa.Integer),
)
_COMPLETIONS = sa.table(
    _TABLE,
    sa.column("id", sa.Integer),
    sa.column("session_id", sa.Integer),
    sa.column("user_id", sa.String),
    sa.column("item_id", sa.String),
    sa.column("completed_at", sa.DateTime(timezone=True)),
    sa.column("source", sa.String),
    sa.column("watched_seconds", sa.Integer),
    sa.column(_COLUMN, sa.Integer),
)


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _has_column(bind) -> bool:
    return _COLUMN in {c["name"] for c in sa.inspect(bind).get_columns(_TABLE)}


def _live_shares(bind) -> list[dict]:
    """``{"_id", "_exclusive"}`` for each live completion, in completion order."""
    done = bind.execute(
        sa.select(
            _COMPLETIONS.c.id, _COMPLETIONS.c.session_id, _COMPLETIONS.c.user_id,
            _COMPLETIONS.c.item_id, _COMPLETIONS.c.completed_at, _COMPLETIONS.c.source,
        ).order_by(_COMPLETIONS.c.completed_at, _COMPLETIONS.c.id)
    ).all()
    if not any(c.source == "live" for c in done):
        return []
    # Only rows with exclusive time can add to a share.
    sittings: dict[tuple, list] = defaultdict(list)
    for s in bind.execute(
        sa.select(_SESSIONS).where(_SESSIONS.c.exclusive_seconds > 0)
    ).all():
        sittings[(s.user_id, s.item_id)].append((s.id, _utc(s.started_at), s.exclusive_seconds))

    shares, previous = [], {}
    for c in done:
        title, at = (c.user_id, c.item_id), _utc(c.completed_at)
        if c.source == "live":
            since = at - _COMPLETION_WINDOW
            if title in previous and previous[title] > since:
                since = previous[title]
            share = sum(
                seconds for row_id, started, seconds in sittings[title]
                if row_id == c.session_id or (started is not None and since <= started <= at)
            )
            shares.append({"_id": c.id, "_exclusive": share})
        previous[title] = at
    return shares


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_column(bind):
        op.add_column(_TABLE, sa.Column(_COLUMN, sa.Integer(), server_default="0", nullable=False))

    bind.execute(
        sa.update(_COMPLETIONS)
        .where(_COMPLETIONS.c.source == "history")
        .values({_COLUMN: _COMPLETIONS.c.watched_seconds})
    )
    statement = (
        sa.update(_COMPLETIONS)
        .where(_COMPLETIONS.c.id == sa.bindparam("_id"))
        .values({_COLUMN: sa.bindparam("_exclusive")})
    )
    shares = _live_shares(bind)
    for i in range(0, len(shares), _BATCH):
        bind.execute(statement, shares[i:i + _BATCH])


def downgrade() -> None:
    if _has_column(op.get_bind()):
        op.drop_column(_TABLE, _COLUMN)
