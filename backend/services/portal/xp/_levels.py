"""
Player level from cumulative XP.

Level curve (quadratic):
  XP_for_level(n) = 50 * n * (n + 1)
  Level 1   =         0 XP  (the start, see level_floor_xp)
  Level 5   =     1,500 XP  (~2 weeks)
  Level 10  =     5,500 XP  (~2 months)
  Level 20  =    21,000 XP  (~6 months)
  Level 30  =    46,500 XP  (~1.5 years)
  Level 40  =    82,000 XP  (~3 years)
  Level 50  =   127,500 XP  (~5 years, max)
"""
MIN_LEVEL = 1
MAX_LEVEL = 50


def xp_for_level(level: int) -> int:
    """Total cumulative XP needed to reach ``level`` above the first (see ``level_floor_xp``)."""
    return 50 * level * (level + 1)


def level_floor_xp(level: int) -> int:
    """Total XP at which ``level`` starts: 0 for the first level, ``xp_for_level`` above it."""
    return 0 if level <= MIN_LEVEL else xp_for_level(level)


def level_from_xp(total_xp: int) -> int:
    """Compute level from total cumulative XP; every player starts at ``MIN_LEVEL``."""
    level = MIN_LEVEL
    while level < MAX_LEVEL and xp_for_level(level + 1) <= total_xp:
        level += 1
    return level
