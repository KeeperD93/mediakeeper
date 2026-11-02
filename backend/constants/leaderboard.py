"""Periods the portal leaderboard can rank players over."""
from enum import StrEnum


class LeaderboardPeriod(StrEnum):
    TODAY = "today"
    WEEK = "week"
    MONTH = "month"
    ALL = "all"
