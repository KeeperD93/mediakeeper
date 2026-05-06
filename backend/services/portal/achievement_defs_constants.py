"""Constants for the achievement system: secret themes, title rewards, tier names."""

# Map secret achievement IDs to their CSS theme class suffix.
# Used by the frontend to apply unique thematic effects (particles, colors, etc.).
SECRET_THEMES = {
    "secret_first_play": "first",
    "secret_early_bird": "dawn",
    "secret_night_owl": "night",
    "secret_christmas": "xmas",
    "secret_halloween": "halloween",
    "secret_valentine": "valentine",
    "secret_no_life": "glitch",
    "secret_purist": "vo",
    "secret_allnight": "allnight",
    "secret_dedication": "crown",
    "secret_newyear": "newyear",
    "secret_classic": "classic",
    "secret_insomnia": "insomnia",
    "secret_king": "king",
    "secret_friday13": "friday13",
    "secret_indecisive": "indecisive",
    "secret_summer": "summer",
    "secret_nostalgia": "nostalgia",
    "secret_pilot": "pilot",
    "secret_ghost": "ghost",
    "secret_double": "double",
    "secret_4k": "fourk",
    "secret_easter": "easter",
    "secret_total": "total",
    "secret_lonely": "lonely",
    "secret_triple": "triple",
    "secret_ultramarathon": "ultramarathon",
    "secret_pipi": "pipi",
    "secret_zapper": "zapper",
    "secret_butterfly": "butterfly",
    "secret_bgNoise": "bgNoise",
    "secret_sunday": "sunday",
    "secret_bilingual": "bilingual",
    "secret_sync": "sync",
    "secret_countdown": "countdown",
    "secret_late": "late",
    "secret_gourmet": "gourmet",
    "secret_ultimate_collector": "ultimateCollector",
}

# Titles awarded by specific achievements (max tier or secrets).
# Value is an i18n key resolved by the frontend.
TITLE_REWARDS = {
    "movie_buff_5": "portal.titles.projectionist",
    "serial_fan_5": "portal.titles.bingeMaster",
    "regular_6": "portal.titles.tireless",
    "marathoner_5": "portal.titles.sleepless",
    "globe_trotter_5": "portal.titles.worldCitizen",
    "chatty_3": "portal.titles.bigTalker",
    "rewatch_king_5": "portal.titles.replayAddict",
    "competitor_6": "portal.titles.eternalChampion",
    "flight_time_6": "portal.titles.eternalSpectator",
    "collector_6": "portal.titles.supremeCollector",
    "master_of_genre_3": "portal.titles.maestro",
    "secret_dedication": "portal.titles.eternal",
    "secret_allnight": "portal.titles.watcher",
    "secret_christmas": "portal.titles.santaClaus",
    "secret_king": "portal.titles.uncontestedKing",
    "secret_insomnia": "portal.titles.insomniac",
    "secret_ultramarathon": "portal.titles.superhuman",
    "secret_ultimate_collector": "portal.titles.omniscient",
    # Mastery meta-achievements (one per category).
    "meta_master_watching":   "portal.titles.virtuoso",
    "meta_master_dedication": "portal.titles.unwavering",
    "meta_master_diversity":  "portal.titles.eclectic",
    "meta_master_special":    "portal.titles.fated",
    "meta_master_community":  "portal.titles.unifier",
    "meta_master_ranking":    "portal.titles.champion",
    "meta_master_profile":    "portal.titles.accomplished",
}

# Tier display names (1=Bronze..6=Supreme). Tier 6 is reserved for the
# rarest standard families (and the hardest secrets) that warrant the
# top "mythic" rarity colour — see _rarity_label in achievements_profile.
TIER_NAMES = {1: "bronze", 2: "silver", 3: "gold", 4: "platinum", 5: "mythic", 6: "supreme"}

# Secondary category for secret achievements so they also show in their
# thematic category (in addition to the "Secrets" category). Keys = ach_id.
SECONDARY_CATEGORIES: dict[str, str] = {
    # special (seasonal / event-driven)
    "secret_first_play": "special",
    "secret_christmas": "special",
    "secret_halloween": "special",
    "secret_valentine": "special",
    "secret_newyear": "special",
    "secret_summer": "special",
    "secret_friday13": "special",
    "secret_easter": "special",
    "secret_countdown": "special",
    # dedication (time-of-day, streaks, endurance)
    "secret_early_bird": "dedication",
    "secret_night_owl": "dedication",
    "secret_no_life": "dedication",
    "secret_allnight": "dedication",
    "secret_dedication": "dedication",
    "secret_insomnia": "dedication",
    "secret_lonely": "dedication",
    "secret_ultramarathon": "dedication",
    "secret_sunday": "dedication",
    "secret_late": "dedication",
    "secret_gourmet": "dedication",
    # watching (playback behaviour)
    "secret_purist": "watching",
    "secret_classic": "watching",
    "secret_indecisive": "watching",
    "secret_nostalgia": "watching",
    "secret_pilot": "watching",
    "secret_ghost": "watching",
    "secret_double": "watching",
    "secret_4k": "watching",
    "secret_pipi": "watching",
    "secret_zapper": "watching",
    "secret_bgNoise": "watching",
    "secret_bilingual": "watching",
    # ranking
    "secret_king": "ranking",
    # community
    "secret_triple": "community",
    "secret_sync": "community",
    # diversity
    "secret_butterfly": "diversity",
    # meta (profile achievements)
    "secret_total": "meta",
    "secret_ultimate_collector": "meta",
}

# Achievements that must NOT count toward any meta ("master of category")
# because they are either one-person-only by design or circular.
EXCLUSIVE_FROM_META: set[str] = {
    "secret_first_play",           # whoever clicks play first on the instance
    "secret_ultimate_collector",   # requires all other trophies → circular dep
}

# Achievements whose check is intentionally a stub — the underlying signal
# (Emby "date added" metadata, pause/resume events, leaderboard history,
# etc.) is not wired yet. They stay declared so the catalogue remains
# stable across releases, but the runner skips their condition_type and
# the profile payload excludes them from `total_count` / `items` so the
# global progression percentage exposed to the UI reflects what is
# actually attainable.
PLACEHOLDER_IDS: frozenset[str] = frozenset({
    # Only ``secret_pipi`` remains sealed: it is gated on pause/resume
    # event tracking, which the playback collector does not emit yet.
    "secret_pipi",
})
