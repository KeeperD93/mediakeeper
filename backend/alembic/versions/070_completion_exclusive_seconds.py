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
  to the completion, its own row included. The sittings kept counting after the
  title was watched (end credits, a second device on the same account): all
  they watched since, known from the completion's watched time, is taken off as
  if watched alone. No part gets a floor, which would credit a sitting added
  since (an earlier completion deleted, statistics merged). Exact when that
  time was watched alone, lower when it was shared. The clock checks it: until
  the title counted, a sitting watched at most the time since it started;
  since then, at most the time to its last poll. Below those bounds sittings
  were removed (one deleted, or left out of the window by merged statistics),
  and the most the sittings can have watched since is taken off. The share
  stays at or below the collector's, unless sittings were both removed and
  added, a removed sitting watched less than the time the others spent not
  playing (it goes unnoticed), or a player went silent across the count and
  caught up after (its clock is then too short): the share can then be too
  high by at most what the removed sitting watched, or that catch-up.
- Offline (``--sql``), only the column and the ``history`` step render: the
  ``live`` backfill reads the rows, and live completions keep 0 without it.

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
# A poll credits at most the time since the row's reference, which trails the poll
# by up to this much (``MAX_CARRY_SECONDS``), frozen as it stood.
_MAX_CARRY_SECONDS = 10

_SESSIONS = sa.table(
    "playback_sessions",
    sa.column("id", sa.Integer),
    sa.column("user_id", sa.String),
    sa.column("item_id", sa.String),
    sa.column("started_at", sa.DateTime(timezone=True)),
    sa.column("last_tick_at", sa.DateTime(timezone=True)),
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


def _clock(s, at: datetime, *, own: bool) -> tuple[float, float]:
    """The least and the most sitting ``s`` can have watched since ``at``: until then
    it watched at most the time since it started; since then, at most the time to
    its last poll, plus a carry, unless its player was silent at ``at`` and caught up."""
    watched = s.watched_seconds or 0
    if s.last_tick_at is None and not own:
        return 0, 0  # never polled (rebuilt history): it cannot have moved since
    least = max(0, watched - (at - _utc(s.started_at)).total_seconds()) if s.started_at else 0
    if s.last_tick_at is None:
        return least, watched
    return least, max(0, min(watched, (_utc(s.last_tick_at) - at).total_seconds() + _MAX_CARRY_SECONDS))


def _share(done, own, others: list) -> int:
    """The exclusive time the collector fixed on ``done``, from its own row and the
    ``others`` sittings; at most that, but for the limits of the module docstring."""
    sittings = [own, *others]
    exclusive = sum(s.exclusive_seconds or 0 for s in sittings)
    # What the sittings watched after the title counted, less those removed since,
    # plus those added.
    after = sum(s.watched_seconds or 0 for s in sittings) - done.watched_seconds
    at = _utc(done.completed_at)
    low, high = _clock(own, at, own=True)
    for s in others:
        least, most = _clock(s, at, own=False)
        low, high = low + least, high + most
    if after < low:
        # Sittings were removed since: the most those left can have watched since comes off.
        return max(0, exclusive - round(max(after, high)))
    return max(0, exclusive - after)


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
        op.execute("-- Offline SQL mode: the live completion backfill is online-only; live completions keep 0.")
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
