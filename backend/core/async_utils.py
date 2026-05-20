"""Async helpers shared across the backend."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Coroutine

_default_logger = logging.getLogger("mediakeeper.background")


def safe_create_task(
    coro: Coroutine[Any, Any, Any],
    *,
    name: str | None = None,
    logger: logging.Logger | None = None,
) -> asyncio.Task:
    """Schedule a fire-and-forget coroutine and log any exception it raises.

    A bare ``asyncio.create_task(coro)`` swallows unhandled exceptions
    silently (``RuntimeWarning: coroutine ... was never awaited``). This
    wrapper attaches a ``done_callback`` that reports unhandled
    exceptions via the standard logger so background failures do not
    disappear.

    Returns the task so callers that need to track it (cancel, await,
    expose status) keep the same handle as before.
    """
    task = asyncio.create_task(coro, name=name)
    log = logger or _default_logger

    def _log_exception(t: asyncio.Task) -> None:
        if t.cancelled():
            return
        exc = t.exception()
        if exc is not None:
            log.exception(
                "Background task %r failed: %s",
                t.get_name(),
                exc,
            )

    task.add_done_callback(_log_exception)
    return task
