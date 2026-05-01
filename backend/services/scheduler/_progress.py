"""Progression en memory des tasks du scheduler (no persistance BDD)."""

_progress: dict[str, dict] = {}


def update_progress(task_key: str, current: int, total: int, label: str = "") -> None:
    """Met up to date la progression d'une task (called from les handlers)."""
    _progress[task_key] = {"current": current, "total": total, "label": label}


def get_progress(task_key: str) -> dict | None:
    """Return la progression d'une task ou None."""
    return _progress.get(task_key)


def clear_progress(task_key: str) -> None:
    """Supprime la progression d'une task (fin d'execution)."""
    _progress.pop(task_key, None)
