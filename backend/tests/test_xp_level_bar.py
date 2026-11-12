"""The level bar rounds halves up, the same on the digest and the profile page."""
import pytest

from models.portal.profile import UserProfile
from services.portal import daily_digest_sources as dd_sources
from services.portal.xp import level_bar_percent

# Same table as the interface test of levelBarPercent: both sides must agree.
LEVEL_BAR_CASES = [
    (1, 0, 0),
    (1, 50, 17),
    (2, 450, 50),
    (3, 500, 0),
    (3, 610, 3),
    (3, 650, 13),
    (3, 658, 15),
    (3, 998, 100),
    (50, 127_500, 100),
]


@pytest.mark.parametrize(("level", "xp", "percent"), LEVEL_BAR_CASES)
def test_level_bar_percent_rounds_halves_up(level, xp, percent):
    assert level_bar_percent(level, xp) == percent


@pytest.mark.parametrize(("level", "xp", "percent"), LEVEL_BAR_CASES)
def test_daily_digest_bar_matches_the_profile_bar(level, xp, percent):
    """12.5 % reads 13 in the digest, as on the profile page (not 12)."""
    assert dd_sources.level_info(UserProfile(level=level, xp=xp))["percent"] == percent
