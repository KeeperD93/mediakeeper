"""Trophies earned by holding others: Collector, Veteran, the Masters, the Ultimate collector.

A held tier goes when the pass gave it, and would not give it once the trophies of the hour
are gone. "Gave it" is judged without the tier itself: Collector does not count itself, and
Veteran reads the level without its own XP, so two tiers cannot hold each other up. The
tiers kept are rebuilt from the bottom, adding each tier the pass would grant on what the
player still holds, until none is added; the order does not change the outcome, as holding
more never makes a tier harder to reach.
"""
from collections.abc import Mapping
from dataclasses import dataclass

from services.portal.achievement_defs import (
    META_TARGET_CATEGORY,
    achievements_for_category,
)
from services.portal.achievement_defs_constants import PLACEHOLDER_IDS
from services.portal.xp import level_from_xp

from ._context import AchievementInfo

_COLLECTOR = "achievements_unlocked"
_VETERAN = "profile_level"
_META = "meta"
_ULTIMATE = "secret_ultimate_collector"
_CASCADE_CONDITIONS = frozenset({_COLLECTOR, _VETERAN, _META, _ULTIMATE})


@dataclass(frozen=True)
class Holdings:
    held: frozenset[str]
    xp: int
    ledger: Mapping[str, int]
    achievements: Mapping[str, AchievementInfo]


@dataclass(frozen=True)
class CascadeOutcome:
    removed: dict[str, int]
    kept_nowhere: list[str]
    kept_gifts: list[str]


def _value(tier: AchievementInfo, owned: set[str], holdings: Holdings) -> int:
    """What the pass would store for ``tier`` if the player owned ``owned``, ``tier`` aside."""
    others = owned - {tier.id}
    if tier.condition_type == _COLLECTOR:
        return len(others)
    if tier.condition_type == _VETERAN:
        lost = sum(holdings.ledger.get(a, 0) for a in holdings.held - others)
        return level_from_xp(max(0, holdings.xp - lost)) or 1
    if tier.condition_type == _META:
        target = META_TARGET_CATEGORY.get(tier.id)
        return sum(a in others for a in achievements_for_category(target)) if target else 0
    total_others = len(holdings.achievements) - 1
    return int(total_others > 0 and len(others) >= total_others)


def _met(tier: AchievementInfo, owned: set[str], holdings: Holdings) -> bool:
    return _value(tier, owned, holdings) >= tier.threshold


def cascade(holdings: Holdings, removed: set[str], gifts: set[str]) -> CascadeOutcome:
    """The tiers to take back once ``removed`` go, each with the value the pass would store."""
    tiers = sorted(
        a for a in holdings.held - removed
        if a not in PLACEHOLDER_IDS and holdings.achievements[a].condition_type in _CASCADE_CONDITIONS
    )
    judged = [
        a for a in tiers
        if a not in gifts and _met(holdings.achievements[a], set(holdings.held), holdings)
    ]
    owned = set(holdings.held) - removed - set(judged)
    added = True
    while added:
        added = False
        for tier_id in judged:
            if tier_id not in owned and _met(holdings.achievements[tier_id], owned, holdings):
                owned.add(tier_id)
                added = True
    return CascadeOutcome(
        removed={a: _value(holdings.achievements[a], owned, holdings) for a in judged if a not in owned},
        kept_nowhere=[a for a in tiers if a not in gifts and a not in judged],
        kept_gifts=[a for a in tiers if a in gifts],
    )
