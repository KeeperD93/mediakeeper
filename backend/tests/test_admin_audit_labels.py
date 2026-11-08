"""Every action the user drawer's Audit tab can list has a label in each language."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.portal import admin_users_constants as constants

_LOCALES = Path(__file__).resolve().parents[2] / "frontend" / "src" / "locales"

# Recorded without a target user, so no user's Audit tab can list them.
_INSTANCE_WIDE_ACTIONS = {
    constants.ACTION_DEBUG_ACHIEVEMENT_RESET_ALL,
    constants.ACTION_DEBUG_ACHIEVEMENT_RECHECK_ALL,
    constants.ACTION_DEBUG_ZONE_CORRECTION,
    constants.ACTION_SYSTEM_TIMEZONE_CHANGED,
}
_ACTIONS_LISTED_PER_USER = sorted(
    value
    for name, value in vars(constants).items()
    if name.startswith("ACTION_") and value not in _INSTANCE_WIDE_ACTIONS
)


def _has_label(labels: dict, action: str) -> bool:
    section, _, key = action.partition(".")
    return key in labels.get(section, {})


@pytest.mark.parametrize("locale", ["fr", "en"])
def test_every_action_listed_per_user_has_a_label(locale):
    messages = json.loads((_LOCALES / f"{locale}.json").read_text(encoding="utf-8"))
    labels = messages["requestsAdmin"]["users"]["audit"]
    assert [a for a in _ACTIONS_LISTED_PER_USER if not _has_label(labels, a)] == []
