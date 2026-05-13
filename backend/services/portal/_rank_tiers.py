"""Title + rank-tier lookups shared by the ranking, stats and digest layers.

Extracted from ``profile_stats_ranking`` to keep that module under the
300-line cap when the leaderboard helpers grew to support the dedicated
``/portal/leaderboard`` page. The functions stay re-exported from
``profile_stats_ranking`` for backwards compatibility.
"""
from __future__ import annotations


def title_for_level(level: int) -> str:
    """Map user level → i18n title key."""
    if level >= 50: return "legend"
    if level >= 30: return "master"
    if level >= 20: return "expert"
    if level >= 12: return "passionate"
    if level >= 6:  return "regular"
    if level >= 3:  return "amateur"
    return "spectator"


def tier_for_title(title_key: str | None) -> int | None:
    """Resolve the rarity tier (1-6) of an unlocked-via-trophy title key."""
    if not title_key:
        return None
    try:
        from services.portal.achievement_defs import TITLE_REWARDS, ACHIEVEMENT_DEFS
        for ach_id, t_key in TITLE_REWARDS.items():
            if t_key == title_key:
                ach_def = next((d for d in ACHIEVEMENT_DEFS if d["id"] == ach_id), None)
                if ach_def:
                    return ach_def.get("tier", 1)
                break
    except Exception:  # noqa: S110 -- best-effort fallback, silently degrades to default behaviour
        pass
    return None


def tier_for_level(level: int) -> str:
    """Map current level → visual rank tier."""
    if level >= 50: return "legendary"
    if level >= 40: return "master"
    if level >= 30: return "diamond"
    if level >= 20: return "platinum"
    if level >= 11: return "gold"
    if level >= 6:  return "silver"
    return "bronze"
