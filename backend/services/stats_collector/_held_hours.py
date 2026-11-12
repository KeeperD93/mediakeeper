"""The watched hours of a playback's start, held until its player proves it plays.

A player switched off seconds into a title leaves Emby moving the session alone,
and nothing tells it from a real start until the position Emby saves at the
first resume point of the library (3 % by default). Until then the row's hours,
what a day streak reads, wait here: paid once the player saves next to the
session or the row ends normally, dropped when it ends judged lost on a position
still saved at 0. The seconds are counted as before, except that a held row never
takes its user's share of a poll from another row of that user.
"""
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from models.playback_stats import PlaybackSession

from ._measure import add_to_hour, exclusive_shares
from ._player_reports import Proof, Verdict


@dataclass(frozen=True)
class _Held:
    hours: dict[str, int]
    lost: bool  # judged lost on its last saved 0: dropped if the row ends so


# Row ``session_key`` -> what it holds. In memory: a restart forgets at most the
# start of a playback. Changed only once a collector pass is committed.
_held: dict[str, _Held] = {}


def _pay(row: PlaybackSession, hours: dict[str, int]) -> None:
    if not hours:
        return
    paid = dict(row.watched_by_hour or {})  # a new object so the JSON column is flagged dirty
    for hour, seconds in hours.items():
        paid[hour] = paid.get(hour, 0) + seconds
    row.watched_by_hour = paid


class HeldHours:
    """What one collector pass changes in ``_held``, kept aside until the pass is committed."""

    def __init__(self) -> None:
        self._pending = dict(_held)
        self._this_poll: set[str] = set()  # rows whose share of this poll is held

    def judge(self, row: PlaybackSession, verdict: Verdict) -> None:
        """Start, keep or pay the row's hold on this poll's verdict."""
        key, proof = row.session_key, verdict.proof
        held = self._pending.get(key)
        if held is None and proof is not Proof.AT_ZERO:
            return
        if held is not None and proof is Proof.SAVED:
            _pay(row, self._pending.pop(key).hours)
            return
        if proof in (Proof.AT_ZERO, Proof.ZERO_UNJUDGED):
            # Only a saved 0 judges the player, lost or not: a save far from the
            # session or a failed read keeps the last judgement.
            held = _Held(held.hours if held else {}, verdict.lost)
        self._pending[key] = held
        self._this_poll.add(key)

    def shares(self, progress: list[tuple[PlaybackSession, str, int]]) -> dict[PlaybackSession, int]:
        """``exclusive_shares``, where a held row only gets its user's share of a
        poll in which no other row of that user moved. Rows held at once share as before."""
        free = [entry for entry in progress if entry[0].session_key not in self._this_poll]
        shares = exclusive_shares(free)
        served = {user for _, user, seconds in free if seconds > 0}
        shares.update(exclusive_shares([
            entry for entry in progress if entry[0].session_key in self._this_poll and entry[1] not in served
        ]))
        return shares

    def add(self, row: PlaybackSession, at: datetime, seconds: int) -> None:
        """File ``seconds`` under the hour of ``at``: on the row, or aside while it is held."""
        key = row.session_key
        if key in self._this_poll:
            held = self._pending[key]
            self._pending[key] = _Held(add_to_hour(held.hours, at, seconds), held.lost)
        else:
            row.watched_by_hour = add_to_hour(row.watched_by_hour, at, seconds)

    def close(self, row: PlaybackSession) -> None:
        """The row ends: what it holds is paid, unless its player was judged lost."""
        held = self._pending.pop(row.session_key, None)
        if held is not None and not held.lost:
            _pay(row, held.hours)

    def commit(self, active: Iterable[PlaybackSession]) -> None:
        """The pass is saved: keep what it holds for the rows still active."""
        keys = {row.session_key for row in active}
        _held.clear()
        _held.update({key: held for key, held in self._pending.items() if key in keys})
