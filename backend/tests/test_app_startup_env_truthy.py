"""_env_truthy unifies env-var truthy parsing across readers.

Pins the MK_DEBUG consistency fix: "on" (and whitespace/case variants) must
be recognised as truthy by the single shared helper, so setup_logging and the
deployment-warning helpers can no longer disagree.
"""
from __future__ import annotations

import pytest

from core.app_startup import _env_truthy


@pytest.mark.parametrize(
    "value", ["true", "True", "1", "yes", "YES", "on", "ON", " on ", "true "],
)
def test_env_truthy_accepts_recognised_values(monkeypatch, value):
    monkeypatch.setenv("MK_TEST_TRUTHY_FLAG", value)
    assert _env_truthy("MK_TEST_TRUTHY_FLAG") is True


@pytest.mark.parametrize("value", ["false", "0", "no", "off", "", "  ", "maybe"])
def test_env_truthy_rejects_other_values(monkeypatch, value):
    monkeypatch.setenv("MK_TEST_TRUTHY_FLAG", value)
    assert _env_truthy("MK_TEST_TRUTHY_FLAG") is False


def test_env_truthy_unset_is_false(monkeypatch):
    monkeypatch.delenv("MK_TEST_TRUTHY_FLAG", raising=False)
    assert _env_truthy("MK_TEST_TRUTHY_FLAG") is False
