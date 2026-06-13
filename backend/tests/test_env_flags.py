"""env_truthy / env_int: single source of truth for env-flag and int parsing.

Pins the MK_DEBUG consistency fix: "on" (and whitespace/case variants) must be
recognised as truthy by the shared helper that logging, CSP, CORS and the
deployment-warning helpers all route through. env_int pins the safe-fallback
contract so a malformed integer env var never crashes the process at boot.
"""
from __future__ import annotations

import logging

import pytest

from core.env_flags import env_int, env_truthy


@pytest.mark.parametrize(
    "value", ["true", "True", "1", "yes", "YES", "on", "ON", " on ", "true "],
)
def test_env_truthy_accepts_recognised_values(monkeypatch, value):
    monkeypatch.setenv("MK_TEST_TRUTHY_FLAG", value)
    assert env_truthy("MK_TEST_TRUTHY_FLAG") is True


@pytest.mark.parametrize("value", ["false", "0", "no", "off", "", "  ", "maybe"])
def test_env_truthy_rejects_other_values(monkeypatch, value):
    monkeypatch.setenv("MK_TEST_TRUTHY_FLAG", value)
    assert env_truthy("MK_TEST_TRUTHY_FLAG") is False


def test_env_truthy_unset_is_false(monkeypatch):
    monkeypatch.delenv("MK_TEST_TRUTHY_FLAG", raising=False)
    assert env_truthy("MK_TEST_TRUTHY_FLAG") is False


@pytest.mark.parametrize("value,expected", [("60", 60), ("0", 0), ("-5", -5), (" 42 ", 42)])
def test_env_int_parses_valid_values(monkeypatch, value, expected):
    monkeypatch.setenv("MK_TEST_INT", value)
    assert env_int("MK_TEST_INT", 99) == expected


@pytest.mark.parametrize("value", ["abc", "1.5", "0x10", "", "  "])
def test_env_int_falls_back_on_invalid_or_blank(monkeypatch, value):
    monkeypatch.setenv("MK_TEST_INT", value)
    assert env_int("MK_TEST_INT", 99) == 99


def test_env_int_unset_returns_default(monkeypatch):
    monkeypatch.delenv("MK_TEST_INT", raising=False)
    assert env_int("MK_TEST_INT", 99) == 99


def test_env_int_warns_on_invalid_value(monkeypatch, caplog):
    monkeypatch.setenv("MK_TEST_INT", "abc")
    with caplog.at_level(logging.WARNING, logger="mediakeeper.env"):
        assert env_int("MK_TEST_INT", 7) == 7
    assert any("Invalid integer" in r.message for r in caplog.records)
