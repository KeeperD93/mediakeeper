"""Catalogue integrity checks for the achievement system.

Both the pytest meta-test (``backend/tests/test_achievements_integrity.py``)
and the optional startup validator hook into the same set of helpers, so a
drift caught in CI is the same drift the runtime would refuse to start on.

A drift here means: an `id` that appears twice across the three definition
collections, a `next_tier_id` that points to nothing, a `condition_type`
declared in the catalogue but never implemented (or vice-versa), a tier
chain whose thresholds go backwards, a secret without its CSS theme, an
i18n key without a translation, or a meta target whose category is empty.

The helpers return lists of strings — one diagnostic per violation — so
callers can either ``raise`` the lot or merely log them.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from services.portal.achievement_defs import (
    ACHIEVEMENT_DEFS,
    META_DEFS,
    META_TARGET_CATEGORY,
    SECRET_THEMES,
    EXCLUSIVE_FROM_META,
    achievements_for_category,
)
from services.portal.achievement_defs_constants import PLACEHOLDER_IDS
from services.portal.achievement_defs_secrets import SECRET_DEFS

# ─── Source-of-truth: the condition_types each check pass implements. ───
#
# Kept inline (rather than parsed from the check files) so the contract
# is explicit and reviewable in one place. Adding a new condition_type
# means: declare it here, implement it in a check pass, then add a def.
KNOWN_CONDITION_TYPES: frozenset[str] = frozenset({
    # check_standard
    "watch_movies", "watch_series", "night_watch", "audio_languages",
    "subtitle_languages", "rewatch_count", "genre_diversity",
    "requests_created", "chat_messages", "marathon_hours", "streak_days",
    "weekend_plays", "season_binge", "library_explorer",
    # check_progression
    "leaderboard_top10", "leaderboard_top5", "leaderboard_top3",
    "leaderboard_first", "achievements_unlocked", "profile_level",
    "avatar_changed", "member_years", "title_equipped", "tickets_created",
    "total_watch_hours", "requests_approved", "speed_runner",
    "binge_session", "genre_master", "events_created", "surprise_used",
    "series_completed", "decades_watched",
    "lists_public_created", "lists_max_items",
    # check_secrets_a
    "secret_first_play", "secret_early_bird", "secret_newyear",
    "secret_classic", "secret_friday13", "secret_indecisive",
    "secret_summer", "secret_nostalgia", "secret_ghost", "secret_double",
    "secret_4k",
    # check_secrets_b (incl. placeholders)
    "secret_countdown", "secret_sunday", "secret_bilingual",
    "secret_bgNoise", "secret_ultramarathon", "secret_butterfly",
    "secret_triple", "secret_zapper", "secret_gourmet",
    "secret_ultimate_collector", "secret_purist", "secret_allnight",
    "secret_no_life", "secret_king", "secret_pilot", "secret_lonely",
    "secret_late", "secret_pipi", "secret_sync",
    # seasonal/themed secrets that have their own condition_type
    "secret_christmas", "secret_halloween", "secret_valentine",
    "secret_easter", "secret_total",
    # meta
    "meta",
})

# Tier chains whose thresholds intentionally do not strictly grow because
# the underlying signal is binary or stage-gated rather than additive.
_NON_MONOTONIC_FAMILIES: frozenset[str] = frozenset({
    "competitor",   # 1/1/1/1/3/12 — top-N positions, not a counter
})


def collect_all_ids() -> list[str]:
    """Return every declared id, in declaration order."""
    return [d["id"] for d in ACHIEVEMENT_DEFS]


def find_duplicate_ids() -> list[str]:
    """ids that appear in more than one definition entry."""
    seen: set[str] = set()
    dups: list[str] = []
    for d in ACHIEVEMENT_DEFS:
        if d["id"] in seen:
            dups.append(d["id"])
        else:
            seen.add(d["id"])
    return dups


def find_orphan_condition_types() -> list[str]:
    """condition_types declared in defs but absent from the implementation set."""
    declared = {d.get("condition_type") for d in ACHIEVEMENT_DEFS}
    declared.discard(None)
    return sorted(declared - KNOWN_CONDITION_TYPES)


def find_unused_condition_types() -> list[str]:
    """condition_types listed as implemented but never referenced by a def."""
    declared = {d.get("condition_type") for d in ACHIEVEMENT_DEFS}
    declared.discard(None)
    return sorted(KNOWN_CONDITION_TYPES - declared)


def find_broken_next_tier_ids() -> list[tuple[str, str]]:
    """Returns (def_id, missing_target) tuples for each broken next_tier_id."""
    all_ids = set(collect_all_ids())
    broken: list[tuple[str, str]] = []
    for d in ACHIEVEMENT_DEFS:
        nxt = d.get("next_tier_id")
        if nxt and nxt not in all_ids:
            broken.append((d["id"], nxt))
    return broken


def find_non_monotonic_chains() -> list[tuple[str, list[int]]]:
    """Walk every tier chain and report families whose thresholds decrease.

    Whitelisted families (``competitor``) are skipped on purpose — the
    semantics there are non-additive.
    """
    by_id = {d["id"]: d for d in ACHIEVEMENT_DEFS}
    seen_roots: set[str] = set()
    issues: list[tuple[str, list[int]]] = []

    for d in ACHIEVEMENT_DEFS:
        if d.get("next_tier_id") is None and not _has_predecessor(d["id"], by_id):
            continue
        # Walk only from the tier-1 root of each chain to avoid duplicates.
        root_id = _find_chain_root(d["id"], by_id)
        if root_id in seen_roots:
            continue
        seen_roots.add(root_id)
        family = root_id.rsplit("_", 1)[0] if root_id.rsplit("_", 1)[-1].isdigit() else root_id
        if family in _NON_MONOTONIC_FAMILIES:
            continue
        thresholds = _walk_chain_thresholds(root_id, by_id)
        if any(b <= a for a, b in zip(thresholds, thresholds[1:])):
            issues.append((root_id, thresholds))
    return issues


def find_secrets_without_theme() -> list[str]:
    """Secret defs missing a SECRET_THEMES entry (frontend renders nothing)."""
    return sorted({
        d["id"] for d in SECRET_DEFS
        if d["id"] not in SECRET_THEMES
    })


def find_meta_targets_with_no_members() -> list[str]:
    """Meta achievements pointing at a category that no def actually feeds."""
    issues: list[str] = []
    for d in META_DEFS:
        target = META_TARGET_CATEGORY.get(d["id"])
        if not target:
            issues.append(f"{d['id']}: no META_TARGET_CATEGORY entry")
            continue
        members = achievements_for_category(target)
        if not members:
            issues.append(f"{d['id']}: target category '{target}' has no members")
    return issues


def find_exclusive_from_meta_orphans() -> list[str]:
    """EXCLUSIVE_FROM_META entries that no longer match any declared id."""
    all_ids = set(collect_all_ids())
    return sorted(EXCLUSIVE_FROM_META - all_ids)


def find_placeholder_orphans() -> list[str]:
    """PLACEHOLDER_IDS entries that no longer match any declared id."""
    all_ids = set(collect_all_ids())
    return sorted(PLACEHOLDER_IDS - all_ids)


# ── i18n integrity (FR + EN parity) ─────────────────────────────────────

_REPO_ROOT = Path(__file__).resolve().parents[3]
_LOCALE_FR = _REPO_ROOT / "frontend" / "src" / "locales" / "fr.json"
_LOCALE_EN = _REPO_ROOT / "frontend" / "src" / "locales" / "en.json"


def _load_portal_achievements_keys(path: Path) -> set[str] | None:
    """Return the catalogue keys declared in the locale file, or
    ``None`` when the source JSON is unreachable.

    The runtime Docker image only ships the compiled frontend bundle
    (``/app/frontend-dist/``), not the source ``frontend/src/locales``
    tree. Returning ``None`` lets the consumer distinguish « file
    unreachable, skip the check » from « file present but the key is
    absent, real drift ».
    """
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return set((data.get("portal", {}).get("achievements", {}) or {}).keys())


def find_missing_i18n_keys() -> list[str]:
    """Defs whose name_key/description_key has no entry in FR or EN.

    Each locale file is checked independently: when the source JSON
    is unreachable (typical Docker runtime that ships only the
    compiled bundle), the corresponding side of the check is silently
    skipped rather than reporting every key as missing. The other
    locale, if reachable, is still validated.
    """
    fr_keys = _load_portal_achievements_keys(_LOCALE_FR)
    en_keys = _load_portal_achievements_keys(_LOCALE_EN)
    if fr_keys is None and en_keys is None:
        return []
    issues: list[str] = []
    suffix_re = re.compile(r"^portal\.achievements\.")
    for d in ACHIEVEMENT_DEFS:
        for field in ("name_key", "description_key"):
            full = d.get(field) or ""
            if not full.startswith("portal.achievements."):
                continue
            short = suffix_re.sub("", full)
            if fr_keys is not None and short not in fr_keys:
                issues.append(f"{d['id']} {field}={full} missing in fr.json")
            if en_keys is not None and short not in en_keys:
                issues.append(f"{d['id']} {field}={full} missing in en.json")
    return issues


# ── Aggregate runners ───────────────────────────────────────────────────

def collect_violations() -> list[str]:
    """Run every check and return human-readable diagnostics.

    An empty list means the catalogue is consistent.
    """
    violations: list[str] = []

    for dup in find_duplicate_ids():
        violations.append(f"duplicate id: {dup}")
    for orphan in find_orphan_condition_types():
        violations.append(f"orphan condition_type (declared, not implemented): {orphan}")
    for unused in find_unused_condition_types():
        violations.append(f"unused condition_type (implemented, never declared): {unused}")
    for src, missing in find_broken_next_tier_ids():
        violations.append(f"{src} → next_tier_id '{missing}' does not exist")
    for root, thresholds in find_non_monotonic_chains():
        violations.append(f"non-monotonic threshold chain rooted at {root}: {thresholds}")
    for sid in find_secrets_without_theme():
        violations.append(f"secret without SECRET_THEMES entry: {sid}")
    for issue in find_meta_targets_with_no_members():
        violations.append(f"meta target has no members: {issue}")
    for ex in find_exclusive_from_meta_orphans():
        violations.append(f"EXCLUSIVE_FROM_META references unknown id: {ex}")
    for ph in find_placeholder_orphans():
        violations.append(f"PLACEHOLDER_IDS references unknown id: {ph}")
    for missing in find_missing_i18n_keys():
        violations.append(f"i18n: {missing}")

    return violations


def assert_catalogue_consistent() -> None:
    """Raise ``ValueError`` if any drift is detected. Used by the boot hook."""
    violations = collect_violations()
    if violations:
        bullets = "\n  - ".join(violations)
        raise ValueError(f"achievement catalogue drift detected:\n  - {bullets}")


# ── Internal helpers ────────────────────────────────────────────────────

def _has_predecessor(target_id: str, by_id: dict[str, dict]) -> bool:
    return any(d.get("next_tier_id") == target_id for d in by_id.values())


def _find_chain_root(any_id: str, by_id: dict[str, dict]) -> str:
    cur = any_id
    while True:
        prev = next(
            (d["id"] for d in by_id.values() if d.get("next_tier_id") == cur),
            None,
        )
        if prev is None:
            return cur
        cur = prev


def _walk_chain_thresholds(root_id: str, by_id: dict[str, dict]) -> list[int]:
    thresholds: list[int] = []
    cur: str | None = root_id
    while cur is not None and cur in by_id:
        thresholds.append(int(by_id[cur].get("threshold") or 0))
        cur = by_id[cur].get("next_tier_id")
    return thresholds
