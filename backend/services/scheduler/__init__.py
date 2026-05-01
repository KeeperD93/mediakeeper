"""
Scheduler service — Mediakeeper task planner.

Each configurable task is defined in TASK_DEFINITIONS. The config
(interval, enabled) is stored in the DB (scheduler_tasks). The scheduler
recharge la config all les 60s.

Tasks NOT handled here (hardcoded in main.py as critical):
  - stats_collection : 15s
  - library_cache    : 3600s

Package split into modules (Rule 9, <= 300 lines).
"""
from ._progress import clear_progress, get_progress, update_progress
from ._scheduler import Scheduler, get_scheduler, init_scheduler
from ._tasks import TASK_DEFINITIONS

__all__ = [
    "Scheduler",
    "TASK_DEFINITIONS",
    "clear_progress",
    "get_progress",
    "get_scheduler",
    "init_scheduler",
    "update_progress",
]
