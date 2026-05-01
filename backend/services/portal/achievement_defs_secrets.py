"""
Secret achievement definitions — unique, never stacked.

Each secret has its own `condition_type` that maps to a check in the
achievements checks module. The `secret_theme` (via SECRET_THEMES) triggers
a unique CSS visual effect on the frontend when unlocked.

condition_type values used here include:
  - secret_first_play, secret_early_bird, night_watch (shared with tiered)
  - secret_christmas, secret_halloween, secret_valentine, secret_newyear
  - secret_friday13, secret_easter, secret_summer
  - secret_no_life, secret_purist, secret_allnight, streak_days (shared)
  - secret_classic, secret_king, secret_indecisive, secret_nostalgia
  - secret_pilot, secret_ghost, secret_double, secret_4k, secret_total
  - secret_lonely, secret_triple, secret_ultramarathon, secret_pipi
  - secret_zapper, secret_butterfly, secret_bgNoise, secret_sunday
  - secret_bilingual, secret_sync, secret_countdown, secret_late
  - secret_gourmet, secret_ultimate_collector
"""

SECRET_DEFS: list[dict] = [
    # First Blood — first ever play
    {"id": "secret_first_play", "category": "secret", "name_key": "portal.achievements.secretFirstPlay", "description_key": "portal.achievements.secretFirstPlay_desc", "icon": "Sparkles", "tier": 2, "xp_reward": 40, "threshold": 1, "condition_type": "secret_first_play", "next_tier_id": None, "secret": True, "sort_order": 300},

    # Early Bird — play between 5:00-6:00
    {"id": "secret_early_bird", "category": "secret", "name_key": "portal.achievements.secretEarlyBird", "description_key": "portal.achievements.secretEarlyBird_desc", "icon": "Sunrise", "tier": 3, "xp_reward": 40, "threshold": 1, "condition_type": "secret_early_bird", "next_tier_id": None, "secret": True, "sort_order": 201},

    # Night Owl — 50+ plays between 00:00-05:00
    {"id": "secret_night_owl", "category": "secret", "name_key": "portal.achievements.secretNightOwl", "description_key": "portal.achievements.secretNightOwl_desc", "icon": "Moon", "tier": 4, "xp_reward": 200, "threshold": 50, "condition_type": "night_watch", "next_tier_id": None, "secret": True, "sort_order": 202},

    # Christmas Spirit — watch xmas content in december
    {"id": "secret_christmas", "category": "secret", "name_key": "portal.achievements.secretChristmas", "description_key": "portal.achievements.secretChristmas_desc", "icon": "TreePine", "tier": 3, "xp_reward": 40, "threshold": 1, "condition_type": "secret_christmas", "next_tier_id": None, "secret": True, "sort_order": 203},

    # Trick or Treat — watch horror on oct 31
    {"id": "secret_halloween", "category": "secret", "name_key": "portal.achievements.secretHalloween", "description_key": "portal.achievements.secretHalloween_desc", "icon": "Skull", "tier": 3, "xp_reward": 40, "threshold": 1, "condition_type": "secret_halloween", "next_tier_id": None, "secret": True, "sort_order": 204},

    # Valentine — watch romance on feb 14
    {"id": "secret_valentine", "category": "secret", "name_key": "portal.achievements.secretValentine", "description_key": "portal.achievements.secretValentine_desc", "icon": "Heart", "tier": 3, "xp_reward": 40, "threshold": 1, "condition_type": "secret_valentine", "next_tier_id": None, "secret": True, "sort_order": 205},

    # No Life — 24h watched in 48h window
    {"id": "secret_no_life", "category": "secret", "name_key": "portal.achievements.secretNoLife", "description_key": "portal.achievements.secretNoLife_desc", "icon": "MonitorPlay", "tier": 4, "xp_reward": 200, "threshold": 1, "condition_type": "secret_no_life", "next_tier_id": None, "secret": True, "sort_order": 206},

    # The Purist — 50 plays in original version
    {"id": "secret_purist", "category": "secret", "name_key": "portal.achievements.secretPurist", "description_key": "portal.achievements.secretPurist_desc", "icon": "Languages", "tier": 4, "xp_reward": 100, "threshold": 50, "condition_type": "secret_purist", "next_tier_id": None, "secret": True, "sort_order": 207},

    # Ultimate All-Nighter — play from 22:00 to 06:00 non-stop
    {"id": "secret_allnight", "category": "secret", "name_key": "portal.achievements.secretAllnight", "description_key": "portal.achievements.secretAllnight_desc", "icon": "Eye", "tier": 4, "xp_reward": 200, "threshold": 1, "condition_type": "secret_allnight", "next_tier_id": None, "secret": True, "sort_order": 208},

    # Faithful — 365 consecutive days
    {"id": "secret_dedication", "category": "secret", "name_key": "portal.achievements.secretDedication", "description_key": "portal.achievements.secretDedication_desc", "icon": "Crown", "tier": 6, "xp_reward": 1200, "threshold": 365, "condition_type": "streak_days", "next_tier_id": None, "secret": True, "sort_order": 309},

    # Bonne Year — watch at midnight Jan 1
    {"id": "secret_newyear", "category": "secret", "name_key": "portal.achievements.secretNewYear", "description_key": "portal.achievements.secretNewYear_desc", "icon": "PartyPopper", "tier": 3, "xp_reward": 40, "threshold": 1, "condition_type": "secret_newyear", "next_tier_id": None, "secret": True, "sort_order": 310},

    # The Classic — film before 1970
    {"id": "secret_classic", "category": "secret", "name_key": "portal.achievements.secretClassic", "description_key": "portal.achievements.secretClassic_desc", "icon": "Clapperboard", "tier": 3, "xp_reward": 40, "threshold": 1, "condition_type": "secret_classic", "next_tier_id": None, "secret": True, "sort_order": 311},

    # Insomniaque — 100 plays after midnight
    {"id": "secret_insomnia", "category": "secret", "name_key": "portal.achievements.secretInsomnia", "description_key": "portal.achievements.secretInsomnia_desc", "icon": "BedDouble", "tier": 5, "xp_reward": 200, "threshold": 100, "condition_type": "night_watch", "next_tier_id": None, "secret": True, "sort_order": 312},

    # The King — #1 for 12 consecutive months
    {"id": "secret_king", "category": "secret", "name_key": "portal.achievements.secretKing", "description_key": "portal.achievements.secretKing_desc", "icon": "Crown", "tier": 6, "xp_reward": 2000, "threshold": 12, "condition_type": "secret_king", "next_tier_id": None, "secret": True, "sort_order": 313},

    # Friday the 13th — horror on Friday the 13th
    {"id": "secret_friday13", "category": "secret", "name_key": "portal.achievements.secretFriday13", "description_key": "portal.achievements.secretFriday13_desc", "icon": "Skull", "tier": 3, "xp_reward": 40, "threshold": 1, "condition_type": "secret_friday13", "next_tier_id": None, "secret": True, "sort_order": 314},

    # The Indecisive — 10 starts without finishing in one day
    {"id": "secret_indecisive", "category": "secret", "name_key": "portal.achievements.secretIndecisive", "description_key": "portal.achievements.secretIndecisive_desc", "icon": "Shuffle", "tier": 3, "xp_reward": 40, "threshold": 1, "condition_type": "secret_indecisive", "next_tier_id": None, "secret": True, "sort_order": 315},

    # Summer Vibes — adventure in July/August
    {"id": "secret_summer", "category": "secret", "name_key": "portal.achievements.secretSummer", "description_key": "portal.achievements.secretSummer_desc", "icon": "SunMedium", "tier": 3, "xp_reward": 40, "threshold": 1, "condition_type": "secret_summer", "next_tier_id": None, "secret": True, "sort_order": 316},

    # The Nostalgic — rewatch after 6 months
    {"id": "secret_nostalgia", "category": "secret", "name_key": "portal.achievements.secretNostalgia", "description_key": "portal.achievements.secretNostalgia_desc", "icon": "Rewind", "tier": 3, "xp_reward": 40, "threshold": 1, "condition_type": "secret_nostalgia", "next_tier_id": None, "secret": True, "sort_order": 317},

    # Pilot — first to watch newly added content
    {"id": "secret_pilot", "category": "secret", "name_key": "portal.achievements.secretPilot", "description_key": "portal.achievements.secretPilot_desc", "icon": "Rocket", "tier": 3, "xp_reward": 40, "threshold": 1, "condition_type": "secret_pilot", "next_tier_id": None, "secret": True, "sort_order": 318},

    # The Ghost — only viewer after midnight
    {"id": "secret_ghost", "category": "secret", "name_key": "portal.achievements.secretGhost", "description_key": "portal.achievements.secretGhost_desc", "icon": "Ghost", "tier": 3, "xp_reward": 40, "threshold": 1, "condition_type": "secret_ghost", "next_tier_id": None, "secret": True, "sort_order": 319},

    # Double — 2 movies back-to-back (< 5min gap)
    {"id": "secret_double", "category": "secret", "name_key": "portal.achievements.secretDouble", "description_key": "portal.achievements.secretDouble_desc", "icon": "Copy", "tier": 3, "xp_reward": 40, "threshold": 1, "condition_type": "secret_double", "next_tier_id": None, "secret": True, "sort_order": 320},

    # 4K Addict — 50 plays in 4K
    {"id": "secret_4k", "category": "secret", "name_key": "portal.achievements.secret4k", "description_key": "portal.achievements.secret4k_desc", "icon": "MonitorUp", "tier": 4, "xp_reward": 100, "threshold": 50, "condition_type": "secret_4k", "next_tier_id": None, "secret": True, "sort_order": 321},

    # Easter — family movie on Easter
    {"id": "secret_easter", "category": "secret", "name_key": "portal.achievements.secretEaster", "description_key": "portal.achievements.secretEaster_desc", "icon": "Egg", "tier": 3, "xp_reward": 40, "threshold": 1, "condition_type": "secret_easter", "next_tier_id": None, "secret": True, "sort_order": 322},

    # The Full Set — watched everything in a library
    {"id": "secret_total", "category": "secret", "name_key": "portal.achievements.secretTotal", "description_key": "portal.achievements.secretTotal_desc", "icon": "CircleCheckBig", "tier": 6, "xp_reward": 1000, "threshold": 1, "condition_type": "secret_total", "next_tier_id": None, "secret": True, "sort_order": 323},

    # The Loner — watching alone on NYE (Dec 31)
    {"id": "secret_lonely", "category": "secret", "name_key": "portal.achievements.secretLonely", "description_key": "portal.achievements.secretLonely_desc", "icon": "CloudRain", "tier": 4, "xp_reward": 40, "threshold": 1, "condition_type": "secret_lonely", "next_tier_id": None, "secret": True, "sort_order": 324},

    # Triple — trilogy in one day
    {"id": "secret_triple", "category": "secret", "name_key": "portal.achievements.secretTriple", "description_key": "portal.achievements.secretTriple_desc", "icon": "Repeat", "tier": 3, "xp_reward": 100, "threshold": 1, "condition_type": "secret_triple", "next_tier_id": None, "secret": True, "sort_order": 325},

    # The Ultimate Marathoner — 24h+ in one session
    {"id": "secret_ultramarathon", "category": "secret", "name_key": "portal.achievements.secretUltramarathon", "description_key": "portal.achievements.secretUltramarathon_desc", "icon": "AlarmClock", "tier": 5, "xp_reward": 600, "threshold": 1, "condition_type": "secret_ultramarathon", "next_tier_id": None, "secret": True, "sort_order": 326},

    # Pause Pipi — pause 2-5min then resume, 5 times
    {"id": "secret_pipi", "category": "secret", "name_key": "portal.achievements.secretPipi", "description_key": "portal.achievements.secretPipi_desc", "icon": "Droplets", "tier": 3, "xp_reward": 40, "threshold": 5, "condition_type": "secret_pipi", "next_tier_id": None, "secret": True, "sort_order": 327},

    # The Zapper — 5 different contents in 10 minutes
    {"id": "secret_zapper", "category": "secret", "name_key": "portal.achievements.secretZapper", "description_key": "portal.achievements.secretZapper_desc", "icon": "Tv", "tier": 3, "xp_reward": 40, "threshold": 1, "condition_type": "secret_zapper", "next_tier_id": None, "secret": True, "sort_order": 328},

    # The Butterfly — 5 genres in one day
    {"id": "secret_butterfly", "category": "secret", "name_key": "portal.achievements.secretButterfly", "description_key": "portal.achievements.secretButterfly_desc", "icon": "Flower2", "tier": 3, "xp_reward": 40, "threshold": 1, "condition_type": "secret_butterfly", "next_tier_id": None, "secret": True, "sort_order": 329},

    # Background Noise — 8h+ session (fell asleep)
    {"id": "secret_bgNoise", "category": "secret", "name_key": "portal.achievements.secretBgNoise", "description_key": "portal.achievements.secretBgNoise_desc", "icon": "Volume2", "tier": 4, "xp_reward": 40, "threshold": 1, "condition_type": "secret_bgNoise", "next_tier_id": None, "secret": True, "sort_order": 330},

    # Sunday — 6h+ on a Sunday
    {"id": "secret_sunday", "category": "secret", "name_key": "portal.achievements.secretSunday", "description_key": "portal.achievements.secretSunday_desc", "icon": "Coffee", "tier": 3, "xp_reward": 40, "threshold": 1, "condition_type": "secret_sunday", "next_tier_id": None, "secret": True, "sort_order": 331},

    # The Bilingual — same movie in 2 different languages
    {"id": "secret_bilingual", "category": "secret", "name_key": "portal.achievements.secretBilingual", "description_key": "portal.achievements.secretBilingual_desc", "icon": "Glasses", "tier": 3, "xp_reward": 40, "threshold": 1, "condition_type": "secret_bilingual", "next_tier_id": None, "secret": True, "sort_order": 332},

    # The Synchronized — same content at same time as another user
    {"id": "secret_sync", "category": "secret", "name_key": "portal.achievements.secretSync", "description_key": "portal.achievements.secretSync_desc", "icon": "Link", "tier": 3, "xp_reward": 40, "threshold": 1, "condition_type": "secret_sync", "next_tier_id": None, "secret": True, "sort_order": 333},

    # 3, 2, 1... Action! — play at exactly midnight (+-1min)
    {"id": "secret_countdown", "category": "secret", "name_key": "portal.achievements.secretCountdown", "description_key": "portal.achievements.secretCountdown_desc", "icon": "TimerReset", "tier": 3, "xp_reward": 40, "threshold": 1, "condition_type": "secret_countdown", "next_tier_id": None, "secret": True, "sort_order": 334},

    # The Straggler — content added 1y+ ago, never watched
    {"id": "secret_late", "category": "secret", "name_key": "portal.achievements.secretLate", "description_key": "portal.achievements.secretLate_desc", "icon": "Archive", "tier": 3, "xp_reward": 40, "threshold": 1, "condition_type": "secret_late", "next_tier_id": None, "secret": True, "sort_order": 335},

    # The Gourmand — watch 12-13h every day for a week
    {"id": "secret_gourmet", "category": "secret", "name_key": "portal.achievements.secretGourmet", "description_key": "portal.achievements.secretGourmet_desc", "icon": "UtensilsCrossed", "tier": 4, "xp_reward": 40, "threshold": 7, "condition_type": "secret_gourmet", "next_tier_id": None, "secret": True, "sort_order": 336},

    # The Ultimate Collector — unlock ALL other trophies
    {"id": "secret_ultimate_collector", "category": "secret", "name_key": "portal.achievements.secretUltimateCollector", "description_key": "portal.achievements.secretUltimateCollector_desc", "icon": "Gem", "tier": 6, "xp_reward": 4800, "threshold": 1, "condition_type": "secret_ultimate_collector", "next_tier_id": None, "secret": True, "sort_order": 999},
]
