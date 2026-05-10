"""Shared "completed views" maths for the profile rewatch + series-
progress stats.

The DB carries two flavours of rows:

  - **Live rows** (``stats_collector``): ``duration_ticks`` is the
    media's RunTimeTicks, ``position_ticks`` is the highest position
    reached during the session.
  - **Legacy rows** (``stats_import`` from Emby's Playback Reporting
    plugin): ``duration_ticks = 0``, ``position_ticks`` is the play
    DURATION (how many seconds the user watched, converted to ticks).

A "completed view" is one full pass through the media. Counting raw
sessions overshoots (a movie watched in five 30-min chunks is 5 rows
but only 1 view); requiring ``ratio >= 0.85`` per session undershoots
on legacy data because there's no per-row runtime to compare against.

The algorithm here merges both signals:

  1. Sessions where ``duration_ticks > 0`` and ``ratio >= 0.85`` count
     as one completed view each.
  2. The remaining play time (legacy rows + sub-threshold live rows)
     is summed up and divided by the media's runtime (fetched from
     Emby) — every full multiple is an additional view.

So Oppenheimer (180 min) watched once in full (180 min) + nine 30-min
chunks (~270 min) = 1 + ⌊270/180⌋ = 2 views. Watching it five times
in chunks but never finishing = 0 views.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from core.http_client import get_internal_client
from services.portal._watch_threshold import WATCHED_THRESHOLD


# Don't try to compute views on items shorter than this — many "Audio"
# rows that slip through the type filter would otherwise count as
# infinite views (runtime ~0 ticks).
_MIN_RUNTIME_TICKS = 60 * 10_000_000  # 60 seconds
_COMPLETE_RATIO = WATCHED_THRESHOLD


def aggregate_play_signal(
    sessions: Iterable,
) -> dict[str, dict]:
    """Group raw playback rows by ``item_id``.

    Each row needs ``item_id``, ``position_ticks`` and ``duration_ticks``
    attributes. Returns ``{item_id: {"complete_sessions": int,
    "residual_ticks": int, "legacy_session_count": int}}``.

    - ``complete_sessions``: live rows that crossed 85 % — 1 view each.
    - ``residual_ticks``: aggregate play time from legacy rows + sub-
      threshold live rows.
    - ``legacy_session_count``: number of legacy/sub-threshold sessions
      contributing to the residual. Used by :func:`complete_views` to
      cap the residual contribution to ``count * runtime`` so a single
      corrupt row that reports an absurd play duration can't inflate
      the view counter (1 session → at most 1 extra view).
    """
    out: dict[str, dict] = defaultdict(lambda: {
        "complete_sessions": 0, "residual_ticks": 0, "legacy_session_count": 0,
    })
    for r in sessions:
        item_id = getattr(r, "item_id", None) or ""
        if not item_id:
            continue
        pos = getattr(r, "position_ticks", 0) or 0
        dur = getattr(r, "duration_ticks", 0) or 0
        if dur > 0 and pos > 0 and (pos / dur) >= _COMPLETE_RATIO:
            out[item_id]["complete_sessions"] += 1
        elif pos > 0:
            out[item_id]["residual_ticks"] += pos
            out[item_id]["legacy_session_count"] += 1
    return dict(out)


def complete_views(
    item_id: str, runtime_ticks: int, agg: dict[str, dict],
) -> int:
    """Resolve ``aggregate_play_signal`` output into a final view count
    for one item, using the runtime fetched from Emby. Items shorter
    than ``_MIN_RUNTIME_TICKS`` (intros, theme music) return 0."""
    if not runtime_ticks or runtime_ticks < _MIN_RUNTIME_TICKS:
        return 0
    data = agg.get(item_id) or {}
    base = data.get("complete_sessions", 0)
    residual = data.get("residual_ticks", 0)
    legacy_n = data.get("legacy_session_count", 0)
    # A single legacy session can't credibly fund more than 1 view's
    # worth of progress: even if its play_duration field is corrupt
    # (e.g. an aggregate of months recorded as a single row), we cap
    # it at runtime so the view counter stays believable.
    capped_residual = min(residual, legacy_n * runtime_ticks)
    return base + (capped_residual // runtime_ticks)


async def fetch_runtimes(
    item_ids: list[str], emby_url: str, emby_key: str,
) -> dict[str, int]:
    """Bulk-fetch ``RunTimeTicks`` for the given Emby item ids."""
    if not item_ids or not emby_url or not emby_key:
        return {}
    out: dict[str, int] = {}
    # Emby caps Items?Ids URL length, so chunk into batches of 50.
    for i in range(0, len(item_ids), 50):
        batch = item_ids[i:i + 50]
        try:
            res = await get_internal_client().get(
                f"{emby_url}/Items",
                params={"Ids": ",".join(batch), "Fields": "RunTimeTicks"},
                headers={"X-Emby-Token": emby_key},
                timeout=10.0,
            )
            if res.status_code != 200:
                continue
            for item in res.json().get("Items", []):
                iid = item.get("Id")
                if iid:
                    out[iid] = int(item.get("RunTimeTicks") or 0)
        except Exception:  # noqa: S112 -- intentional best-effort iteration, skip individual failure
            continue
    return out
