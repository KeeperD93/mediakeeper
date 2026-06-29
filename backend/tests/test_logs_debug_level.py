"""apply_debug_level moves BOTH the logger and the file handler (#484).

The admin "Debug mode" toggle previously set only the logger level, leaving the
file handler filtering DEBUG records out of the log file. The shared helper now
moves both together.
"""
from __future__ import annotations

import logging

import core.app_startup as startup


def test_apply_debug_level_moves_logger_and_file_handler(monkeypatch):
    handler = logging.NullHandler()
    handler.setLevel(logging.INFO)
    monkeypatch.setattr(startup, "_file_handler", handler)
    mk = logging.getLogger("mediakeeper")
    previous = mk.level
    try:
        startup.apply_debug_level(True)
        assert mk.level == logging.DEBUG
        assert handler.level == logging.DEBUG  # the bug: this used to stay INFO

        startup.apply_debug_level(False)
        assert mk.level == logging.INFO
        assert handler.level == logging.INFO
    finally:
        mk.setLevel(previous)


def test_apply_debug_level_tolerates_missing_file_handler(monkeypatch):
    monkeypatch.setattr(startup, "_file_handler", None)
    mk = logging.getLogger("mediakeeper")
    previous = mk.level
    try:
        startup.apply_debug_level(True)  # console-only fallback must not raise
        assert mk.level == logging.DEBUG
    finally:
        mk.setLevel(previous)
