"""Alert event types pushed to the runtime monitoring webhook."""
from enum import Enum


class AlertType(str, Enum):
    """Categories of runtime incidents the monitoring webhook reports.

    Each value is used as the deduplication key for the in-memory debounce.
    """

    DB_UNAVAILABLE = "db_unavailable"
    DB_RECOVERED = "db_recovered"
    SCHEDULER_TASK_CRASHED = "scheduler_task_crashed"
    BACKGROUND_LOOP_CRASHED = "background_loop_crashed"
    BACKUP_FAILED = "backup_failed"
    POOL_SATURATED = "pool_saturated"


# Discord embed colors (decimal). Red = critical, yellow = warning, green = recovery.
ALERT_COLORS: dict[AlertType, int] = {
    AlertType.DB_UNAVAILABLE: 0xE74C3C,
    AlertType.DB_RECOVERED: 0x2ECC71,
    AlertType.SCHEDULER_TASK_CRASHED: 0xE74C3C,
    AlertType.BACKGROUND_LOOP_CRASHED: 0xE74C3C,
    AlertType.BACKUP_FAILED: 0xF1C40F,
    AlertType.POOL_SATURATED: 0xF1C40F,
}


ALERT_TITLES: dict[AlertType, str] = {
    AlertType.DB_UNAVAILABLE: "Database unavailable",
    AlertType.DB_RECOVERED: "Database recovered",
    AlertType.SCHEDULER_TASK_CRASHED: "Scheduler task crashed",
    AlertType.BACKGROUND_LOOP_CRASHED: "Background loop crashed",
    AlertType.BACKUP_FAILED: "Backup failed",
    AlertType.POOL_SATURATED: "Database pool saturated",
}
