"""The level curve the profile page copies: same table as its test of ``xpForLevel``."""
import pytest

from services.portal.xp import xp_for_level


@pytest.mark.parametrize(("level", "xp"), [(1, 100), (16, 13_600), (50, 127_500)])
def test_xp_needed_for_a_level(level, xp):
    assert xp_for_level(level) == xp
