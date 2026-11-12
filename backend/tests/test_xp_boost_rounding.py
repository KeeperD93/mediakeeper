"""A bonus multiplier rounds halves up, on every XP grant."""
from datetime import UTC, datetime, timedelta

import pytest

from models.portal.xp_boost import XpBoostEvent
from services.portal.xp_boost import boosted_xp, multiplier_at

AT = datetime(2026, 3, 7, 20, 0, tzinfo=UTC)


@pytest.mark.parametrize(("xp", "multiplier", "boosted"), [
    (15, 1.5, 23), (7, 1.5, 11), (2, 1.25, 3), (25, 2.3, 58), (40, 2.0, 80), (10, 1.0, 10), (1, 0.4, 0),
])
def test_a_bonus_rounds_to_the_nearest_with_halves_up(xp, multiplier, boosted):
    assert boosted_xp(xp, multiplier) == boosted


def test_overlapping_events_multiply_without_losing_the_half():
    events = [
        XpBoostEvent(
            name=name, multiplier=multiplier, enabled=True,
            starts_at=AT - timedelta(hours=1), ends_at=AT + timedelta(hours=1),
        )
        for name, multiplier in (("Test Event A", 1.15), ("Test Event B", 1.5))
    ]

    assert boosted_xp(20, multiplier_at(events, "daily_login", AT)) == 35  # 20 × 1.725 = 34.5
