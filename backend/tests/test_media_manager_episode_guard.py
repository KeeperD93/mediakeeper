"""``build_episode_name`` rejects negative season/episode (defence in depth).

The HTTP boundary already enforces ``ge=0`` via ``EpisodeNameRequest``, but
``build_episode_name`` can also be called from scripts/tests; a negative
value used to silently produce a malformed ``S-1E..`` name instead of
failing loudly.
"""
from __future__ import annotations

import pytest

from services.media_manager.naming import build_episode_name


def test_build_episode_name_rejects_negative_season():
    with pytest.raises(ValueError):
        build_episode_name("Demo", -1, 1, "Pilot", ".mkv")


def test_build_episode_name_rejects_negative_episode():
    with pytest.raises(ValueError):
        build_episode_name("Demo", 1, -1, "Pilot", ".mkv")


def test_build_episode_name_accepts_zero_boundary():
    # ge=0 boundary: season/episode 0 is valid (e.g. specials).
    assert build_episode_name("Demo", 0, 0, "Special", "") == "Demo - S00E00 - Special"
