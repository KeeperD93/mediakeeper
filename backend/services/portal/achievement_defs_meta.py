"""Meta-achievements: one per category, unlocked when every non-excluded
achievement of that category is itself unlocked (primary OR secondary
category match). Secrets marked EXCLUSIVE_FROM_META are ignored so unique-
to-one-person or circular accomplishments don't block the meta.

Category matching is resolved at check time by achievements_checks_meta,
not baked into a static list — any new trophy added to a category is
picked up automatically.

Each meta lives in the synthetic "mastery" category so it shows together
in the overlay under "Masters". Tier 6 (mythic) + Crown icon convey the
supreme-accomplishment feel.
"""

# target_category = the category we are "mastering".
# threshold is computed dynamically at seed time in achievements_seed so it
# matches the actual number of counted achievements, but we still ship a
# reasonable default here for out-of-band usage.
META_DEFS: list[dict] = [
    {
        "id": "meta_master_watching",
        "target_category": "watching",
        "category": "mastery",
        "name_key": "portal.achievements.metaMasterWatching",
        "description_key": "portal.achievements.metaMasterWatching_desc",
        "icon": "Crown",
        "tier": 6,
        "xp_reward": 2000,
        "threshold": 1,  # recomputed at seed time
        "condition_type": "meta",
        "next_tier_id": None,
        "secret": False,
        "sort_order": 901,
    },
    {
        "id": "meta_master_dedication",
        "target_category": "dedication",
        "category": "mastery",
        "name_key": "portal.achievements.metaMasterDedication",
        "description_key": "portal.achievements.metaMasterDedication_desc",
        "icon": "Crown",
        "tier": 6,
        "xp_reward": 2000,
        "threshold": 1,
        "condition_type": "meta",
        "next_tier_id": None,
        "secret": False,
        "sort_order": 902,
    },
    {
        "id": "meta_master_diversity",
        "target_category": "diversity",
        "category": "mastery",
        "name_key": "portal.achievements.metaMasterDiversity",
        "description_key": "portal.achievements.metaMasterDiversity_desc",
        "icon": "Crown",
        "tier": 6,
        "xp_reward": 2000,
        "threshold": 1,
        "condition_type": "meta",
        "next_tier_id": None,
        "secret": False,
        "sort_order": 903,
    },
    {
        "id": "meta_master_special",
        "target_category": "special",
        "category": "mastery",
        "name_key": "portal.achievements.metaMasterSpecial",
        "description_key": "portal.achievements.metaMasterSpecial_desc",
        "icon": "Crown",
        "tier": 6,
        "xp_reward": 2000,
        "threshold": 1,
        "condition_type": "meta",
        "next_tier_id": None,
        "secret": False,
        "sort_order": 904,
    },
    {
        "id": "meta_master_community",
        "target_category": "community",
        "category": "mastery",
        "name_key": "portal.achievements.metaMasterCommunity",
        "description_key": "portal.achievements.metaMasterCommunity_desc",
        "icon": "Crown",
        "tier": 6,
        "xp_reward": 2000,
        "threshold": 1,
        "condition_type": "meta",
        "next_tier_id": None,
        "secret": False,
        "sort_order": 905,
    },
    {
        "id": "meta_master_ranking",
        "target_category": "ranking",
        "category": "mastery",
        "name_key": "portal.achievements.metaMasterRanking",
        "description_key": "portal.achievements.metaMasterRanking_desc",
        "icon": "Crown",
        "tier": 6,
        "xp_reward": 2000,
        "threshold": 1,
        "condition_type": "meta",
        "next_tier_id": None,
        "secret": False,
        "sort_order": 906,
    },
    {
        "id": "meta_master_profile",
        "target_category": "meta",
        "category": "mastery",
        "name_key": "portal.achievements.metaMasterProfile",
        "description_key": "portal.achievements.metaMasterProfile_desc",
        "icon": "Crown",
        "tier": 6,
        "xp_reward": 2000,
        "threshold": 1,
        "condition_type": "meta",
        "next_tier_id": None,
        "secret": False,
        "sort_order": 907,
    },
]

# Quick lookup: meta_id -> the category it masters.
META_TARGET_CATEGORY: dict[str, str] = {m["id"]: m["target_category"] for m in META_DEFS}
