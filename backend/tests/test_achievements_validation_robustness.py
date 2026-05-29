"""Boot-robustness guards for the achievement catalogue validator.

- A corrupt/missing locale JSON must be skipped (return None) instead of
  crashing the boot validator.
- A next_tier_id cycle must not hang the chain-root / threshold walks.
"""
from __future__ import annotations

from pathlib import Path

from services.portal.achievements_validation import (
    _find_chain_root,
    _load_portal_achievements_keys,
    _walk_chain_thresholds,
)


def test_load_locale_keys_returns_none_on_corrupt_json(tmp_path: Path):
    bad = tmp_path / "fr.json"
    bad.write_text("{ this is : not valid json ", encoding="utf-8")
    assert _load_portal_achievements_keys(bad) is None


def test_load_locale_keys_returns_none_when_missing(tmp_path: Path):
    assert _load_portal_achievements_keys(tmp_path / "nope.json") is None


def test_load_locale_keys_parses_valid_json(tmp_path: Path):
    good = tmp_path / "en.json"
    good.write_text(
        '{"portal": {"achievements": {"first_play_name": "First play"}}}',
        encoding="utf-8",
    )
    assert _load_portal_achievements_keys(good) == {"first_play_name"}


def test_find_chain_root_terminates_on_cycle():
    # A -> B -> A is a synthetic next_tier_id cycle: must return, not hang.
    by_id = {
        "A": {"id": "A", "next_tier_id": "B"},
        "B": {"id": "B", "next_tier_id": "A"},
    }
    assert _find_chain_root("A", by_id) in {"A", "B"}


def test_walk_chain_thresholds_terminates_on_cycle():
    by_id = {
        "A": {"id": "A", "next_tier_id": "B", "threshold": 1},
        "B": {"id": "B", "next_tier_id": "A", "threshold": 2},
    }
    # Each node visited at most once -> finite list, no infinite loop.
    assert _walk_chain_thresholds("A", by_id) == [1, 2]
