"""Daily-cadence dispatch for the scheduler (drift-proof quota recompute).

The quota recompute fires once per local calendar day instead of during a fixed
midnight hour: an hourly interval timer that drifts on the monotonic clock can
otherwise walk out of the 00:00-00:59 window and skip a day. These tests pin the
two dispatch decisions in isolation.
"""
import datetime as _dt

from services.scheduler._scheduler import Scheduler
from services.scheduler._tasks import TASK_DEFINITIONS


def _scheduler() -> Scheduler:
    # The dispatch helpers only read in-memory timers/dates, never the engine.
    return Scheduler(engine=None)


def test_quota_recompute_uses_daily_cadence():
    assert TASK_DEFINITIONS["quota_auto_recompute"].get("daily_cadence") is True


def test_interval_due_compares_against_timer():
    s = _scheduler()
    s._timers["k"] = 100.0
    assert s._interval_due("k", 100.0) is True   # exactly due
    assert s._interval_due("k", 150.0) is True   # past due
    assert s._interval_due("k", 99.0) is False   # not yet
    # Unknown key defaults to "due now" so a fresh task fires on the next tick.
    assert s._interval_due("missing", 0.0) is True


def test_daily_cadence_fires_once_per_local_date():
    s = _scheduler()
    day1 = _dt.date(2026, 6, 18)
    day2 = _dt.date(2026, 6, 19)
    key = "quota_auto_recompute"

    assert s._daily_cadence_ok(key, day1) is True   # first check of the day
    s._cadence_last_date[key] = day1                # dispatch records the date
    assert s._daily_cadence_ok(key, day1) is False  # later/drifted tick: blocked
    assert s._daily_cadence_ok(key, day2) is True   # new day: allowed again


def test_daily_cadence_ok_passes_non_daily_tasks():
    s = _scheduler()
    day = _dt.date(2026, 6, 18)
    assert s._daily_cadence_ok("notifications", day) is True
    s._cadence_last_date["notifications"] = day
    assert s._daily_cadence_ok("notifications", day) is True  # never date-gated
