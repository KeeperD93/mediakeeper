"""Trophies held up by others go with them, judged without themselves."""
import builtins

import pytest

from services.portal.achievement_defs import achievements_for_category
from services.portal.xp import xp_for_level
from services.portal.zone_correction import _cascade
from services.portal.zone_correction._cascade import Holdings, cascade
from services.portal.zone_correction._context import AchievementInfo


def _catalogue(**thresholds: tuple[str, int]) -> dict[str, AchievementInfo]:
    return {
        achievement_id: AchievementInfo(achievement_id, condition, threshold, f"key.{achievement_id}")
        for achievement_id, (condition, threshold) in thresholds.items()
    }


CATALOGUE = _catalogue(
    collector=("achievements_unlocked", 3),
    veteran=("profile_level", 2),
    dawn=("secret_early_bird", 1),
    t1=("watch_movies", 1),
    t2=("watch_movies", 1),
    t3=("watch_movies", 1),
)
LEDGER = {"dawn": 50, "collector": 200, "veteran": 10}


def _holdings(held: set[str], xp: int) -> Holdings:
    return Holdings(frozenset(held), xp, LEDGER, CATALOGUE)


def test_collector_does_not_count_itself():
    # Four held: the collector and three others; one of them goes, two remain.
    outcome = cascade(_holdings({"collector", "dawn", "t1", "t2"}, 0), {"dawn"}, set())
    assert outcome.removed == {"collector": 2}


def test_a_collector_reached_only_by_counting_itself_was_not_given_by_the_pass():
    outcome = cascade(_holdings({"collector", "dawn", "t1"}, 0), {"dawn"}, set())
    assert outcome.removed == {} and outcome.kept_nowhere == ["collector"]


def test_another_trophy_compensates():
    outcome = cascade(_holdings({"collector", "dawn", "t1", "t2", "t3"}, 0), {"dawn"}, set())
    assert outcome.removed == {}


def test_two_tiers_cannot_hold_each_other_up():
    # The collector needs the veteran to count three; the veteran needs the collector's XP.
    held = {"collector", "veteran", "dawn", "t1", "t2"}
    outcome = cascade(_holdings(held, 400), {"dawn"}, set())
    assert outcome.removed == {"collector": 2, "veteran": 1}


def test_a_tier_earned_on_its_own_brings_back_the_one_above():
    held = {"collector", "veteran", "dawn", "t1", "t2"}
    outcome = cascade(_holdings(held, 1000), {"dawn"}, set())
    assert outcome.removed == {}


def test_veteran_reads_the_level_without_its_own_xp():
    # Level 2 only thanks to its own 10 XP: the pass never gave it, so nothing to take back.
    xp = xp_for_level(2) + 5
    outcome = cascade(_holdings({"veteran", "t1"}, xp), set(), set())
    assert outcome.removed == {} and outcome.kept_nowhere == ["veteran"]


def test_a_tier_handed_out_by_an_admin_stays():
    outcome = cascade(_holdings({"collector", "dawn", "t1", "t2"}, 0), {"dawn"}, {"collector"})
    assert outcome.removed == {} and outcome.kept_gifts == ["collector"]


@pytest.mark.parametrize("reverse", [False, True])
def test_the_order_tiers_are_judged_in_changes_nothing(monkeypatch, reverse):
    if reverse:
        monkeypatch.setattr(
            _cascade, "sorted", lambda items: builtins.sorted(items, reverse=True), raising=False,
        )
    held = {"collector", "veteran", "dawn", "t1", "t2"}
    assert cascade(_holdings(held, 1000), {"dawn"}, set()).removed == {}
    assert cascade(_holdings(held, 400), {"dawn"}, set()).removed == {"collector": 2, "veteran": 1}


def test_the_master_of_a_category_goes_with_one_of_its_trophies():
    ranking = achievements_for_category("ranking")
    catalogue = {
        **_catalogue(**{a: ("leaderboard_top10", 1) for a in ranking}),
        **_catalogue(meta_master_ranking=("meta", len(ranking))),
    }
    holdings = Holdings(frozenset({*ranking, "meta_master_ranking"}), 0, {}, catalogue)
    outcome = cascade(holdings, {"competitor_1"}, set())
    assert outcome.removed == {"meta_master_ranking": len(ranking) - 1}


def test_the_ultimate_collector_goes_with_any_trophy():
    catalogue = {**CATALOGUE, **_catalogue(secret_ultimate_collector=("secret_ultimate_collector", 1))}
    holdings = Holdings(frozenset(catalogue), 0, {}, catalogue)
    assert cascade(holdings, {"t1"}, set()).removed == {"secret_ultimate_collector": 0}
