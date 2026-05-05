"""Catalogue integrity meta-tests for the achievement system.

These tests exercise ``services.portal.achievements_validation`` so a drift
between the definitions, the check passes, the constants and the i18n
files surfaces in CI rather than at runtime (or — worse — never).

Each helper is verified independently so a failure points at exactly one
class of drift; ``test_catalogue_is_consistent`` is the bottom-line check
that guards the same assertion the startup validator runs against.
"""
from __future__ import annotations

from services.portal import achievements_validation as av
from services.portal.achievement_defs import ACHIEVEMENT_DEFS


def test_no_duplicate_achievement_ids():
    assert av.find_duplicate_ids() == []


def test_every_condition_type_has_a_check_implementation():
    assert av.find_orphan_condition_types() == []


def test_every_implementation_is_used_by_at_least_one_def():
    assert av.find_unused_condition_types() == []


def test_next_tier_ids_resolve_to_existing_definitions():
    assert av.find_broken_next_tier_ids() == []


def test_tier_chain_thresholds_grow_monotonically_outside_whitelist():
    assert av.find_non_monotonic_chains() == []


def test_every_secret_has_a_theme_mapping():
    assert av.find_secrets_without_theme() == []


def test_meta_targets_resolve_to_non_empty_categories():
    assert av.find_meta_targets_with_no_members() == []


def test_exclusive_from_meta_only_references_known_ids():
    assert av.find_exclusive_from_meta_orphans() == []


def test_placeholder_ids_only_reference_known_ids():
    assert av.find_placeholder_orphans() == []


def test_every_definition_has_fr_and_en_translations():
    # Diagnostics are aggregated to keep the failure readable when several
    # keys are missing at once (e.g. when a new family lands FR-only).
    issues = av.find_missing_i18n_keys()
    assert issues == [], "missing i18n entries:\n" + "\n".join(issues)


def test_catalogue_is_consistent():
    assert av.collect_violations() == []


def test_known_condition_types_covers_curator_and_librarian():
    """Regression check: the new families must remain on the implemented set."""
    assert "lists_public_created" in av.KNOWN_CONDITION_TYPES
    assert "lists_max_items" in av.KNOWN_CONDITION_TYPES


def test_curator_and_librarian_definitions_present():
    """Five tiers each, in the community category, sorted as expected."""
    by_id = {d["id"]: d for d in ACHIEVEMENT_DEFS}
    for family, condition in (
        ("curator", "lists_public_created"),
        ("librarian", "lists_max_items"),
    ):
        for tier in range(1, 6):
            ach_id = f"{family}_{tier}"
            assert ach_id in by_id, f"missing {ach_id}"
            ach = by_id[ach_id]
            assert ach["category"] == "community"
            assert ach["condition_type"] == condition
            assert ach["tier"] == tier
            expected_next = f"{family}_{tier + 1}" if tier < 5 else None
            assert ach.get("next_tier_id") == expected_next
