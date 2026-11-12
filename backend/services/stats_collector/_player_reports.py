"""What the player itself reported, as opposed to what Emby extrapolates.

Emby moves a session's position and refreshes its activity on its own between
two reports of the player, and keeps doing so once the player is gone. While
it plays, the resume position saved for the user only changes on a real report
(about every 10 s): a session running away from it no longer has a player
behind it.
"""
import asyncio
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

import httpx

from constants.playback import TICKS_PER_SECOND, WATCH_ITEM_TYPES
from core.http_client import get_internal_client
from models.playback_stats import PlaybackSession

from ._measure import MAX_CARRY_SECONDS, POLL_INTERVAL_SECONDS, as_utc
from ._resume_zones import resume_zone

logger = logging.getLogger("mediakeeper.stats.collector")

_READ_TIMEOUT_SECONDS = 3.0
# A real player stays within one report of its saved position.
_MAX_REPORT_GAP_TICKS = 30 * TICKS_PER_SECOND
# A row younger than this may still sit on the position saved by an earlier viewing.
_MIN_WATCHED_SECONDS = 60
# A row measured at every poll keeps its reference within one carry of the last poll.
_ON_HOLD_AFTER = timedelta(seconds=2 * POLL_INTERVAL_SECONDS + MAX_CARRY_SECONDS)
# Emby saves 0 at the very start of a title; well past it, on a long title, 0
# means the player never reported from there.
_ZERO_MIN_RUNTIME_TICKS = 3600 * TICKS_PER_SECOND
_ZERO_MIN_SHARE = 0.10
# At normal speed a real report moves the saved position like the clock, give or take one poll and its jitter.
_MAX_CLOCK_GAP_SECONDS = POLL_INTERVAL_SECONDS + 2
# Such moves needed in a row: a single one can be a seek.
_STEPS_TO_TRUST = 2


@dataclass
class _LastStored:
    ticks: int
    changed_at: datetime
    small_steps: int = 0


# (client, library) seen saving its position while playing: the others keep the
# activity rule. Learned again after a restart from the first reports it sees.
_writers: set[tuple[str, str]] = set()
_last_stored: dict[str, _LastStored] = {}
# Devices seen saving their position while playing: before its first save, only
# such a device is held, a known application may run on players that save nothing.
_saving_devices: set[str] = set()


@dataclass(frozen=True)
class StoredPosition:
    ticks: int
    played: bool


class Proof(Enum):
    """What the saved position read now tells of the player, until it proves it plays."""

    SAVED = "saved"  # saved next to the session: the player itself reports
    AT_ZERO = "at_zero"  # still 0 where the rule of a save left at 0 may yet judge the player lost
    NONE = "none"  # read, but neither


@dataclass(frozen=True)
class Verdict:
    lost: bool
    # None when nothing was read or judged (paused, not a video, failed read).
    proof: Proof | None = None


def title_key(session: dict) -> tuple[str, str]:
    return session.get("UserId", ""), session["NowPlayingItem"].get("Id", "")


async def _stored_for_user(
    url: str, api_key: str, user_id: str, item_ids: list[str],
) -> dict[tuple[str, str], StoredPosition]:
    try:
        response = await get_internal_client().get(
            f"{url}/Users/{user_id}/Items",
            headers={"X-Emby-Token": api_key},
            params={"Ids": ",".join(item_ids), "Fields": "UserData", "EnableImages": "false", "EnableUserData": "true"},
            timeout=_READ_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        items = response.json().get("Items", [])
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Saved positions unavailable: %s", type(exc).__name__)
        return {}
    return {
        (user_id, item.get("Id", "")): StoredPosition(
            item["UserData"].get("PlaybackPositionTicks") or 0, bool(item["UserData"].get("Played")),
        )
        for item in items if item.get("UserData")
    }


async def fetch_stored_positions(
    url: str, api_key: str, sessions: list[dict],
) -> dict[tuple[str, str], StoredPosition]:
    """Saved position of each video playing now, per ``title_key``.

    Absent when the read failed, or when two sessions of one user play the same
    title: each overwrites the other's saved position.
    """
    titles = Counter(
        title_key(s) for s in sessions
        if s["NowPlayingItem"].get("Type") in WATCH_ITEM_TYPES and not s.get("PlayState", {}).get("IsPaused", False)
    )
    by_user: dict[str, list[str]] = defaultdict(list)
    for (user_id, item_id), playing in titles.items():
        if playing == 1:
            by_user[user_id].append(item_id)
    results = await asyncio.gather(*(
        _stored_for_user(url, api_key, user_id, item_ids) for user_id, item_ids in by_user.items()
    ))
    return {key: position for result in results for key, position in result.items()}


def _far(first_ticks: int, second_ticks: int) -> bool:
    return abs(first_ticks - second_ticks) > _MAX_REPORT_GAP_TICKS


def _on_hold(row: PlaybackSession, now: datetime) -> bool:
    reference = as_utc(row.last_tick_at)
    return reference is not None and now - reference > _ON_HOLD_AFTER


def _runs_from_save(position: int, saved_ticks: int, row: PlaybackSession | None) -> bool:
    if not _far(position, saved_ticks):
        return False
    # Without a row, a known application only opens one next to what it saved.
    return row is None or (
        (row.watched_seconds or 0) >= _MIN_WATCHED_SECONDS and not _far(row.position_ticks or 0, saved_ticks)
    )


def _last_confirmed(row: PlaybackSession | None, previous_row: PlaybackSession | None, key: str) -> int | None:
    """Where the player was last seen playing: its open row, or its last closed
    one when the session has stayed listed with nothing saved since."""
    if row is not None:
        return row.position_ticks or 0
    last = _last_stored.get(key)
    seen = as_utc(previous_row.last_seen_at) if previous_row is not None else None
    if seen is None or last is None or last.ticks or last.changed_at > seen:
        return None
    return previous_row.position_ticks or 0


def _left_unsaved(position: int, confirmed: int | None, runtime_ticks: int, library: str | None) -> bool:
    """Saved at 0: True when the session is past where the player would have saved."""
    deep_in_long_title = runtime_ticks >= _ZERO_MIN_RUNTIME_TICKS and position >= runtime_ticks * _ZERO_MIN_SHARE
    zone = resume_zone(library)
    if zone is None:
        return deep_in_long_title
    start = zone.start_ticks(runtime_ticks)
    if start is None or position - start <= _MAX_REPORT_GAP_TICKS:
        return False  # Emby rightly keeps 0 there
    # The playback crossed the first position Emby saves without a single save;
    # one that started past it is judged as before.
    crossed = confirmed is not None and confirmed - start <= _MAX_REPORT_GAP_TICKS
    return crossed or deep_in_long_title


def _may_be_left_unsaved(runtime_ticks: int, library: str | None) -> bool:
    """Whether ``_left_unsaved`` can judge this title: Emby saves a resume position, or it is long."""
    zone = resume_zone(library)
    if zone is None:
        return runtime_ticks >= _ZERO_MIN_RUNTIME_TICKS
    return zone.start_ticks(runtime_ticks) is not None


def _moves_like_the_clock(last: _LastStored, ticks: int, now: datetime) -> bool:
    moved = (ticks - last.ticks) / TICKS_PER_SECOND
    return moved > 0 and abs(moved - (now - last.changed_at).total_seconds()) <= _MAX_CLOCK_GAP_SECONDS


def _learn(
    key: str, client: str, device: str, library: str | None, position: int, stored: StoredPosition, now: datetime,
) -> None:
    last = _last_stored.get(key)
    if last is None:
        _last_stored[key] = _LastStored(stored.ticks, now)
        return
    if last.ticks == stored.ticks:
        return
    reported = (
        _moves_like_the_clock(last, stored.ticks, now)
        and not _far(last.ticks, stored.ticks) and not _far(position, stored.ticks)
    )
    last.small_steps = last.small_steps + 1 if reported else 0
    last.ticks, last.changed_at = stored.ticks, now
    if last.small_steps < _STEPS_TO_TRUST:
        return
    if device:
        _saving_devices.add(device)
    if library and (client, library) not in _writers:
        _writers.add((client, library))
        logger.info("Playback reports confirmed: client %s saves its position in library %s", client, library)


def judge_player(
    session: dict,
    key: str,
    row: PlaybackSession | None,
    previous_row: PlaybackSession | None,
    stored: StoredPosition | None,
    now: datetime,
) -> Verdict:
    """Whether this session's position moves without its player, and what proves it plays.

    ``row`` is the session's open row, ``previous_row`` its last closed one.
    Only for an application seen saving its position. Judged before ``_learn``
    adds to what is known, so both answers read the same state.
    """
    item = session["NowPlayingItem"]
    play_state = session.get("PlayState", {})
    if play_state.get("IsPaused", False) or item.get("Type") not in WATCH_ITEM_TYPES:
        _last_stored.pop(key, None)  # what a pause saves says nothing of the playback
        return Verdict(False)
    reference = row or previous_row
    library = reference.library_name if reference else None
    client = session.get("Client", "")
    device = session.get("DeviceId") or ""
    known = (client, library) in _writers
    position = play_state.get("PositionTicks") or 0
    if stored is None:
        # Nothing read this time proves nothing: a row on hold stays on hold,
        # and a leftover does not open one thanks to a failed read.
        if row is not None:
            return Verdict(known and _on_hold(row, now))
        last = _last_stored.get(key)
        return Verdict(known and last is not None and _far(position, last.ticks))
    if stored.ticks > 0:
        lost = known and _runs_from_save(position, stored.ticks, row)
        proof = Proof.NONE if _far(position, stored.ticks) else Proof.SAVED
    else:
        runtime = item.get("RunTimeTicks") or 0
        saving = device in _saving_devices
        confirmed = _last_confirmed(row, previous_row, key) if saving else None
        judged = known and not stored.played
        lost = judged and _left_unsaved(position, confirmed, runtime, library)
        proof = Proof.AT_ZERO if judged and saving and _may_be_left_unsaved(runtime, library) else Proof.NONE
    _learn(key, client, device, library, position, stored, now)
    return Verdict(lost, proof)


def forget_other_sessions(keys: set[str]) -> None:
    for key in _last_stored.keys() - keys:
        del _last_stored[key]
