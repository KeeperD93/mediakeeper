"""Time watched alone, kept on each watched title

A title counts as watched on the time of its own playback rows, but a user
playing two titles at once is credited once per poll: only the row that moved
most gets that time (``playback_sessions.exclusive_seconds``). Watch XP needs
that share as it was when the title counted as watched, which nothing kept:
``playback_completions.exclusive_seconds`` now does.

Backfilled once:
- ``history`` completions: 062 set the exclusive time of a rebuilt row to its
  estimate, so the share equals ``watched_seconds``;
- ``live`` completions: the exclusive seconds of the user's other sittings of
  the same title, from the previous completion of that title (or 30 days back)
  up to the completion, as the collector adds them up, plus its own row's. That
  row kept counting after its title was watched (end credits): what it watched
  since, known from the completion's watched time, is taken off as if watched
  alone. Exact when the end was watched alone and every sitting is still there,
  lower when the end was shared. When a sitting deleted since leaves the
  completion with more time than the sittings left can hold, what the row
  watched since comes from where it stopped instead; a deleted sitting shorter
  than that does not show, and can leave the share up to its length too high.

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
_TICKS_PER_SECOND = 10_000_000
# Share of the runtime the position reaches when a title counts as watched
# (``WATCHED_THRESHOLD``), frozen as it stood.
_WATCHED_AT = 0.85

_SESSIONS = sa.table(
    "playback_sessions",
    sa.column("id", sa.Integer),
    sa.column("user_id", sa.String),
    sa.column("item_id", sa.String),
    sa.column("started_at", sa.DateTime(timezone=True)),
    sa.column("duration_ticks", sa.BigInteger),
    sa.column("position_ticks", sa.BigInteger),
    sa.column("watched_seconds", sa.Integer),
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


def _share(done, own, others: list) -> int:
    """The exclusive time the collector fixed on ``done``, from its own row and
    the ``others`` sittings it added up."""
    own_watched = own.watched_seconds or 0
    # What the own row watched after the title counted.
    after = own_watched - (done.watched_seconds - sum(s.watched_seconds or 0 for s in others))
    if after < 0:
        # A sitting deleted since: what the row played past the point where its title
        # counted, from where it stopped, rather than nothing.
        past = ((own.position_ticks or 0) - (own.duration_ticks or 0) * _WATCHED_AT) / _TICKS_PER_SECOND
        after = min(own_watched, max(0, round(past))) if own.duration_ticks else 0
    return sum(s.exclusive_seconds or 0 for s in others) + max(0, (own.exclusive_seconds or 0) - after)


def _live_shares(bind) -> list[dict]:
    """``{"_id", "_exclusive"}`` for each live completion, in completion order."""
    done = bind.execute(
        sa.select(
            _COMPLETIONS.c.id, _COMPLETIONS.c.session_id, _COMPLETIONS.c.user_id, _COMPLETIONS.c.item_id,
            _COMPLETIONS.c.completed_at, _COMPLETIONS.c.source, _COMPLETIONS.c.watched_seconds,
        ).order_by(_COMPLETIONS.c.completed_at, _COMPLETIONS.c.id)
    ).all()
    if not any(c.source == "live" for c in done):
        return []
    # The sittings of the titles watched live only.
    live = _COMPLETIONS.alias("live")
    sittings: dict[tuple, list] = defaultdict(list)
    for s in bind.execute(sa.select(_SESSIONS).where(sa.exists().where(
        live.c.source == "live", live.c.user_id == _SESSIONS.c.user_id, live.c.item_id == _SESSIONS.c.item_id,
    ))).all():
        sittings[(s.user_id, s.item_id)].append(s)

    shares, previous = [], {}
    for c in done:
        title, at = (c.user_id, c.item_id), _utc(c.completed_at)
        if c.source == "live":
            since = at - _COMPLETION_WINDOW
            if title in previous and previous[title] > since:
                since = previous[title]
            # The own row moves with its watched title (statistics merge): always in the group.
            own = next(s for s in sittings[title] if s.id == c.session_id)
            others = [
                s for s in sittings[title]
                if s.id != c.session_id and s.started_at is not None and since <= _utc(s.started_at) <= at
            ]
            shares.append({"_id": c.id, "_exclusive": _share(c, own, others)})
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
    # ``as_sql`` rather than ``context.is_offline_mode()``: the tests run this step
    # without an Alembic environment.
    if op.get_context().as_sql:
        op.execute("-- Offline SQL mode: the live completion backfill is online-only.")
        return
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
