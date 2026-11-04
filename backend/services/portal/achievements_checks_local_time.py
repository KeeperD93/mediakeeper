"""Achievement pass for the rules that read the local clock of the instance."""
from datetime import UTC, datetime, tzinfo

from sqlalchemy.ext.asyncio import AsyncSession

from models.playback_stats import PlaybackSession
from models.portal.achievement import Achievement
from services.instance_time import to_local, zone_is_chosen
from services.portal.achievements_local_time import (
    LOCAL_TIME_RULES,
    local_plays,
    new_year_rows,
)
from services.portal.achievements_utils import update_progress
from services.portal.play_streak import current_streak, longest_streak
from services.portal.playback_overlap import (
    find_concurrent_other_user_session,
    has_distinct_user_universe,
)

_STREAK = "streak_days"
_LONELY = "secret_lonely"
LOCAL_TIME_CONDITIONS = (*LOCAL_TIME_RULES, _STREAK, _LONELY)


async def _is_lonely(db: AsyncSession, rows: list[PlaybackSession]) -> bool:
    """A new year session no other user was watching during. Needs a second user at all."""
    if not rows or not await has_distinct_user_universe(db):
        return False
    for row in rows:
        if not await find_concurrent_other_user_session(
            db, user_id=row.user_id, started_at=row.started_at, ended_at=row.ended_at,
        ):
            return True
    return False


async def check_local_time(
    db: AsyncSession,
    by_type: dict[str, list[Achievement]],
    user_id: int,
    ua_map: dict,
    unlocked_ids: set[str],
    rows: list[PlaybackSession],
    zone: tzinfo,
) -> list[dict]:
    """Run every rule on the clock of ``zone``. Returns the newly unlocked list."""
    unlocks: list[dict] = []

    async def _apply(ach: Achievement, value: int) -> None:
        if ach.id in unlocked_ids:
            return
        unlock = await update_progress(db, user_id, ach.id, new_value=value, ua_map=ua_map)
        if unlock:
            unlocks.append(unlock)

    plays = local_plays(rows, zone)
    for condition, rule in LOCAL_TIME_RULES.items():
        if condition in by_type:
            value = rule(plays)
            for ach in by_type[condition]:
                await _apply(ach, value)

    # Once a zone is chosen, a tier reached by a past run is earned; the others show the run
    # in progress. Before that nothing changes: a tier is final, and these are not its days.
    if _STREAK in by_type:
        days = {play.at.date() for play in plays}
        today = to_local(datetime.now(UTC), zone).date()
        current = current_streak(days, today)
        longest = 0
        if zone_is_chosen(zone):
            longest = longest_streak(day for day in days if day <= today)
        for ach in by_type[_STREAK]:
            await _apply(ach, longest if longest >= ach.threshold else current)

    if _LONELY in by_type:
        value = int(await _is_lonely(db, new_year_rows(plays)))
        for ach in by_type[_LONELY]:
            await _apply(ach, value)

    return unlocks
