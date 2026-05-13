"""Catalogue integrity meta-tests for the achievement system.

These tests exercise ``services.portal.achievements_validation`` so a drift
between the definitions, the check passes, the constants and the i18n
files surfaces in CI rather than at runtime (or — worse — never).

Each helper is verified independently so a failure points at exactly one
class of drift; ``test_catalogue_is_consistent`` is the bottom-line check
that guards the same assertion the startup validator runs against.
"""
from __future__ import annotations

import json
from pathlib import Path

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


def _first_portal_def_with_name_key() -> dict:
    for d in ACHIEVEMENT_DEFS:
        full = d.get("name_key") or ""
        if full.startswith("portal.achievements."):
            return d
    raise AssertionError("no ACHIEVEMENT_DEFS entry exposes a portal.achievements.* name_key")


def _write_locale(path: Path, keys: list[str]) -> None:
    payload = {"portal": {"achievements": {k: "x" for k in keys}}}
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_missing_i18n_keys_locales_present_returns_empty():
    """Baseline: with both locales reachable, the catalogue has full parity."""
    assert av.find_missing_i18n_keys() == []


def test_missing_i18n_keys_both_files_unreachable_skips_silently(tmp_path, monkeypatch):
    """Docker runtime regression: when neither locale file is on disk, the
    check must skip rather than flag every key as missing (the bug that
    crashed the backend boot when the source ``frontend/src/locales`` tree
    was not shipped in the runtime image).
    """
    missing_fr = tmp_path / "absent_fr.json"
    missing_en = tmp_path / "absent_en.json"
    assert not missing_fr.exists() and not missing_en.exists()
    monkeypatch.setattr(av, "_LOCALE_FR", missing_fr)
    monkeypatch.setattr(av, "_LOCALE_EN", missing_en)

    assert av.find_missing_i18n_keys() == []


def test_missing_i18n_keys_single_file_unreachable_only_flags_present_locale(tmp_path, monkeypatch):
    """If FR is unreachable but EN is on disk with an empty catalogue,
    we expect only `missing in en.json` bullets (FR side silently skipped).
    """
    missing_fr = tmp_path / "absent_fr.json"
    real_en = tmp_path / "en.json"
    _write_locale(real_en, keys=[])
    monkeypatch.setattr(av, "_LOCALE_FR", missing_fr)
    monkeypatch.setattr(av, "_LOCALE_EN", real_en)

    issues = av.find_missing_i18n_keys()
    assert issues, "EN catalogue is empty — at least one missing-key bullet expected"
    assert all("missing in en.json" in i for i in issues)
    assert not any("missing in fr.json" in i for i in issues)


def test_missing_i18n_keys_detects_real_drift_when_both_files_reachable(tmp_path, monkeypatch):
    """Regression guard: the new « unreachable → skip » branch must not
    swallow real drift. When both files are present but one specific key
    is omitted, exactly that key surfaces as a violation on both sides.
    """
    target = _first_portal_def_with_name_key()
    full_key = target["name_key"]
    short_key = full_key[len("portal.achievements."):]
    declared_shorts = sorted({
        (d[f] or "")[len("portal.achievements."):]
        for d in ACHIEVEMENT_DEFS
        for f in ("name_key", "description_key")
        if (d.get(f) or "").startswith("portal.achievements.")
    })
    payload_keys = [k for k in declared_shorts if k != short_key]

    fr_path = tmp_path / "fr.json"
    en_path = tmp_path / "en.json"
    _write_locale(fr_path, keys=payload_keys)
    _write_locale(en_path, keys=payload_keys)
    monkeypatch.setattr(av, "_LOCALE_FR", fr_path)
    monkeypatch.setattr(av, "_LOCALE_EN", en_path)

    issues = av.find_missing_i18n_keys()
    expected_fr = f"{target['id']} name_key={full_key} missing in fr.json"
    expected_en = f"{target['id']} name_key={full_key} missing in en.json"
    assert expected_fr in issues
    assert expected_en in issues
    assert all(full_key in i for i in issues), (
        f"unexpected drift surfaced beyond the omitted key:\n  - "
        + "\n  - ".join(i for i in issues if full_key not in i)
    )


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
