"""Single source of truth for the "validated watch" threshold.

A media is counted as actually watched once the user reached at least
``WATCHED_THRESHOLD`` of its runtime. Below the threshold the play is
treated as a sample / abandon and ignored by Top 20, genre stats, XP,
profile rewatch counters and recent-watches status — all of these used
to embed their own ``0.85`` literal, which made future tuning a search-
and-replace exercise and let the surfaces drift apart.

Two flavours of rows live in ``playback_sessions``:

  - **Live rows** (``stats_collector``): ``duration_ticks`` is the
    media's RunTimeTicks and ``position_ticks`` is the highest position
    reached. ``ratio = position / duration`` is the canonical signal.
  - **Legacy rows** (``stats_import`` from Emby Playback Reporting):
    ``duration_ticks`` is ``0`` / ``NULL`` because the plugin only
    records play time, not media runtime. ``position_ticks`` is then a
    play-DURATION in ticks, so any session ≥ 1 minute counts as a full
    watch (anything shorter was a quick sample).

``watched_session_filter()`` returns a SQLAlchemy expression matching
both flavours; ``session_meets_threshold()`` is the Python equivalent
for callers that have already loaded the row.
"""
from __future__ import annotations

from sqlalchemy import and_, or_

from models.playback_stats import PlaybackSession


WATCHED_THRESHOLD = 0.85

# 1 minute in Emby ticks (100 ns units). Floor for legacy
# Playback-Reporting rows whose ``duration_ticks`` is 0/NULL: shorter
# plays are sampling, not viewing.
LEGACY_MIN_TICKS = 600_000_000


def watched_session_filter():
    """SQL filter selecting only rows that crossed the watch threshold."""
    return or_(
        and_(
            PlaybackSession.duration_ticks > 0,
            PlaybackSession.position_ticks
            >= PlaybackSession.duration_ticks * WATCHED_THRESHOLD,
        ),
        and_(
            or_(
                PlaybackSession.duration_ticks == 0,
                PlaybackSession.duration_ticks.is_(None),
            ),
            PlaybackSession.position_ticks >= LEGACY_MIN_TICKS,
        ),
    )


def session_meets_threshold(
    position_ticks: int | None, duration_ticks: int | None,
) -> bool:
    """Python mirror of ``watched_session_filter`` for in-memory rows."""
    pos = position_ticks or 0
    dur = duration_ticks or 0
    if dur > 0:
        return pos >= dur * WATCHED_THRESHOLD
    return pos >= LEGACY_MIN_TICKS
