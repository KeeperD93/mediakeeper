"""The value a check pass would store for a trophy of the hour, on one clock, for one player.

Same rules as the pass, read on the plays it would read, with nothing written: the local
clock rules, the day streak, the lonely new year, the all-nighter, the king, Competitor.
"""
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from models.playback_stats import PlaybackSession
from services.instance_time import to_local
from services.portal.achievements_checks_local_time import START_DAY_STREAKS, _is_lonely
from services.portal.achievements_checks_progression import COMPETITOR_POSITIONS
from services.portal.achievements_local_time import (
    LOCAL_TIME_RULES,
    LocalPlay,
    local_plays,
    new_year_rows,
)
from services.portal.play_streak import current_streak, longest_streak
from services.portal.playback_algorithms import (
    KING_REQUIRED_CONSECUTIVE_MONTHS,
    all_night_chain_in,
    holds_12_consecutive_top1_months,
)
from services.portal.watch_days import watch_days

from ._context import AchievementInfo, Context, Side, is_imported

_STREAK = "streak_days"
_LONELY = "secret_lonely"
_ALLNIGHT = "secret_allnight"
_KING = "secret_king"
_COMPETITOR_LIMITS = dict(COMPETITOR_POSITIONS)
HOUR_CONDITIONS = frozenset({
    *LOCAL_TIME_RULES, _STREAK, _LONELY, _ALLNIGHT, _KING, *_COMPETITOR_LIMITS,
})


@dataclass(frozen=True)
class PlayerPlays:
    user_id: int
    rows: list[PlaybackSession]
    spans: list[tuple[datetime, datetime]]
    native_spans: list[tuple[datetime, datetime]]
    emby_ids: list[str]


class Judge:
    """``native`` drops the imported history: a removal it changes rests on that history."""

    def __init__(self, db: AsyncSession, ctx: Context, plays: PlayerPlays) -> None:
        self._db = db
        self._ctx = ctx
        self._plays = plays
        self._local: dict[tuple[int, bool], list[LocalPlay]] = {}
        self._days: dict[tuple[int, bool, bool], set[date]] = {}

    def _rows(self, native: bool) -> list[PlaybackSession]:
        rows = self._plays.rows
        return [row for row in rows if not is_imported(row.session_key)] if native else rows

    def _local_plays(self, side: Side, native: bool) -> list[LocalPlay]:
        key = (id(side), native)
        if key not in self._local:
            self._local[key] = local_plays(self._rows(native), side.zone)
        return self._local[key]

    def _streak(self, ach: AchievementInfo, side: Side, native: bool, *, started: bool) -> int:
        """The day streak on the start days of the plays, or on the days watched."""
        key = (id(side), native, started)
        if key not in self._days:
            self._days[key] = (
                {play.at.date() for play in self._local_plays(side, native)} if started
                else watch_days(self._rows(native), side.zone)
            )
        days = self._days[key]
        today = to_local(datetime.now(UTC), side.zone).date()
        longest = longest_streak(day for day in days if day <= today)
        return longest if longest >= ach.threshold else current_streak(days, today)

    async def value(self, ach: AchievementInfo, side: Side, *, native: bool = False) -> int:
        condition = ach.condition_type
        if condition in _COMPETITOR_LIMITS:
            limit = _COMPETITOR_LIMITS[condition]
            return sum(rank <= limit for rank in side.competitor_ranks.get(self._plays.user_id, []))
        if condition == _KING:
            leaders = self._ctx.king_leaders_native if native else side.king_leaders
            held = self._ctx.universe and bool(self._plays.emby_ids) and (
                holds_12_consecutive_top1_months(leaders, self._plays.emby_ids)
            )
            return KING_REQUIRED_CONSECUTIVE_MONTHS if held else 0
        if condition == _ALLNIGHT:
            spans = self._plays.native_spans if native else self._plays.spans
            return int(all_night_chain_in(spans, side.zone))
        if condition == _STREAK:
            if ach.id in START_DAY_STREAKS:
                return self._streak(ach, side, native, started=True)
            # Regular moved from start days to days watched: on each clock a tier either rule
            # holds is held, so the change of rule alone neither takes one back nor spares one.
            return max(
                self._streak(ach, side, native, started=False),
                self._streak(ach, side, native, started=True),
            )

        plays = self._local_plays(side, native)
        if condition in LOCAL_TIME_RULES:
            return LOCAL_TIME_RULES[condition](plays)
        if condition == _LONELY:
            return int(await _is_lonely(self._db, new_year_rows(plays)))
        raise ValueError(f"not a trophy of the hour: {condition}")
