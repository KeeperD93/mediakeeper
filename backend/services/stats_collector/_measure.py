"""Continuous watch-time measurement, one Emby poll at a time.

Each poll adds the smaller of the elapsed time and the position progress since
the row's reference: a pause, a stall or a frozen player adds nothing, a seek
forward only adds the time really spent. Emby keeps advancing the position on
its side every second, so the precision follows the polling interval.
"""
import re
from collections import Counter
from datetime import datetime, timedelta, timezone

from constants.playback import TICKS_PER_SECOND, WATCH_HOUR_KEY_FORMAT, WATCH_ITEM_TYPES
from services.watch_hours import spread_over_hours

# Delay between two polls: the precision of every measured session.
POLL_INTERVAL_SECONDS = 5
# The position moves by jerks from one poll to the next: what a poll cannot
# credit stays available to the next ones, up to this much (a seek or a stall
# leaves no more behind).
MAX_CARRY_SECONDS = 10
# A first poll this close to the start of the title is a real start, not a
# resume: those seconds were watched before the collector saw the session
# (players often report the start late, after buffering).
FRESH_START_MAX_SECONDS = 30
# Some players make Emby drop a paused session after about a minute: when the
# same Emby session plays again within this delay, it is the same viewing.
RESUME_WINDOW = timedelta(minutes=30)
# With nothing really played for this long, the row ends at its last real second.
SILENCE_LIMIT = timedelta(minutes=30)
# A row reopened after Emby dropped the session may start from a position Emby
# made up: what comes back at once stays within what a player can have buffered.
MAX_REOPEN_CREDIT_SECONDS = 300
# A playing player refreshes ``LastActivityDate`` every few seconds. A session
# first seen with an activity older than this is a leftover, not a playback.
CLIENT_SILENCE_LIMIT = timedelta(seconds=60)

_EXTRA_FRACTION_DIGITS = re.compile(r"(\.\d{6})\d+")


def as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def parse_emby_date(value: str | None) -> datetime | None:
    """Emby dates carry 7 fractional digits ("…:50.2057071Z"); Python reads 6."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(_EXTRA_FRACTION_DIGITS.sub(r"\1", value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return as_utc(parsed)


def client_is_alive(session: dict, now: datetime) -> bool:
    """False once the player has been silent for too long (unknown = alive)."""
    last_activity = parse_emby_date(session.get("LastActivityDate"))
    return last_activity is None or now - last_activity <= CLIENT_SILENCE_LIMIT


def player_confirms(session: dict, since: datetime | None) -> bool:
    """True if the player itself reported activity after ``since`` (or reports none).

    While a player is silent (network lost, TV switched off, tab closed) Emby
    may keep the session and move its position on its own: only the player
    can tell how far it really played, once it reports again.
    """
    last_activity = parse_emby_date(session.get("LastActivityDate"))
    since = as_utc(since)
    return last_activity is None or since is None or last_activity > since


def progress_seconds(
    previous_position_ticks: int | None,
    previous_tick_at: datetime | None,
    position_ticks: int | None,
    now: datetime,
) -> int:
    """Seconds really watched since the previous poll of the same row."""
    previous_at = as_utc(previous_tick_at)
    if previous_at is None or previous_position_ticks is None:
        return 0
    elapsed = (now - previous_at).total_seconds()
    position = (position_ticks or 0) / TICKS_PER_SECOND
    progressed = position - previous_position_ticks / TICKS_PER_SECOND
    if progressed < 0:
        # Back near the very start is a restart: what played since counts.
        # Any other jump back adds nothing.
        return int(min(elapsed, position)) if position <= FRESH_START_MAX_SECONDS else 0
    return int(min(elapsed, progressed))


def measure_progress(
    previous_position_ticks: int | None,
    previous_tick_at: datetime | None,
    position_ticks: int,
    now: datetime,
    *,
    paused: bool,
) -> tuple[int, datetime, int]:
    """Seconds to credit, then the row's new reference (time, position).

    The reference only moves by what was credited, so a jerk of the position
    is made up by the following polls. A pause leaves nothing to make up.
    """
    previous_at = as_utc(previous_tick_at)
    if previous_at is None or previous_position_ticks is None:
        return 0, now, position_ticks
    progressed = (position_ticks - previous_position_ticks) / TICKS_PER_SECOND
    if paused or progressed < -MAX_CARRY_SECONDS:
        return progress_seconds(previous_position_ticks, previous_at, position_ticks, now), now, position_ticks
    elapsed = (now - previous_at).total_seconds()
    credit = int(min(elapsed, max(progressed, 0)))
    carried_at = max(previous_at + timedelta(seconds=credit), now - timedelta(seconds=MAX_CARRY_SECONDS))
    carried_position = max(
        previous_position_ticks + credit * TICKS_PER_SECOND,
        position_ticks - MAX_CARRY_SECONDS * TICKS_PER_SECOND,
    )
    return credit, carried_at, carried_position


def fresh_start_seconds(position_ticks: int | None) -> int:
    """Seconds to credit when a new row is first seen near the title's start."""
    seconds = (position_ticks or 0) / TICKS_PER_SECOND
    return int(seconds) if 0 < seconds <= FRESH_START_MAX_SECONDS else 0


def add_to_hour(buckets: dict | None, at: datetime, seconds: int) -> dict | None:
    """Return a new ``{"YYYY-MM-DDTHH": seconds}`` mapping (UTC hours) with ``seconds`` added."""
    if seconds <= 0:
        return buckets
    updated = dict(buckets or {})  # a new object so the JSON column is flagged dirty
    key = as_utc(at).strftime(WATCH_HOUR_KEY_FORMAT)
    updated[key] = updated.get(key, 0) + seconds
    return updated


def history_measure(session_key: str, item_type: str, started_at: datetime, seconds: int) -> dict:
    """Measurement columns of a row rebuilt from history (played duration only)."""
    is_video = item_type in WATCH_ITEM_TYPES
    return {
        "emby_session_key": session_key,
        "watched_seconds": seconds,
        "exclusive_seconds": seconds if is_video else 0,
        "watched_by_hour": spread_over_hours(started_at, seconds) if is_video and seconds else None,
        "measured": False,
    }


def exclusive_shares(progress: list[tuple[object, str, int]]) -> dict[object, int]:
    """Per user, a poll counts once even when several devices play at once.

    ``progress`` holds ``(row, emby_user_id, seconds)``; the row that moved the
    most gets the user's time for this poll, the others get nothing. Several
    rows moving at once are bounded by the poll: a carried jerk of one of them
    is not extra time for the user.
    """
    best: dict[str, tuple[object, int]] = {}
    moved: Counter[str] = Counter()
    for row, user_id, seconds in progress:
        if seconds > 0:
            moved[user_id] += 1
            if user_id not in best or seconds > best[user_id][1]:
                best[user_id] = (row, seconds)
    return {
        row: min(seconds, POLL_INTERVAL_SECONDS) if moved[user_id] > 1 else seconds
        for user_id, (row, seconds) in best.items()
    }
