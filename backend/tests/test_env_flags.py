"""env_truthy: single source of truth for boolean env-flag parsing.

Pins the MK_DEBUG consistency fix: "on" (and whitespace/case variants) must be
recognised as truthy by the shared helper that logging, CSP, CORS and the
deployment-warning helpers all route through.
"""
from __future__ import annotations

import pytest

from core.env_flags import env_truthy


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
