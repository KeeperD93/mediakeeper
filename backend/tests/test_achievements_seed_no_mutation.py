"""seed_achievements must not mutate the shared ACHIEVEMENT_DEFS thresholds
while still applying the computed meta threshold to the DB row.
"""
from __future__ import annotations

import pytest

from models.portal.achievement import Achievement
from services.portal.achievement_defs import (
    ACHIEVEMENT_DEFS,
    META_TARGET_CATEGORY,
    achievements_for_category,
)
from services.portal.achievements_seed import seed_achievements


@pytest.mark.asyncio
async def test_seed_does_not_mutate_achievement_defs(db_session):
    before = [d.get("threshold") for d in ACHIEVEMENT_DEFS]
    await seed_achievements(db_session)
    after = [d.get("threshold") for d in ACHIEVEMENT_DEFS]
    assert after == before


@pytest.mark.asyncio
async def test_seed_applies_computed_meta_threshold_to_db(db_session):
    meta = next(
        (
            d for d in ACHIEVEMENT_DEFS
            if d.get("condition_type") == "meta" and META_TARGET_CATEGORY.get(d["id"])
        ),
        None,
    )
    assert meta is not None, "catalogue has no meta achievement to assert on"

    await seed_achievements(db_session)

    expected = max(1, len(achievements_for_category(META_TARGET_CATEGORY[meta["id"]])))
    row = await db_session.get(Achievement, meta["id"])
    assert row is not None
    assert row.threshold == expected
