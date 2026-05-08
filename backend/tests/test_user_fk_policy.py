"""Static guard on every foreign key that references ``users.id``.

The GDPR purge job hard-deletes a ``users`` row, so each referencing
column must declare an explicit ``ON DELETE`` policy:

* ``CASCADE`` — the referencing row is account-bound (preferences,
  quotas, achievements, votes…). It cannot survive its owner.
* ``SET NULL`` — the referencing row carries audit, community or
  moderation value (news, tickets, messages, history…). It must
  outlive the owner anonymised.

This file pins the expected policy per column and fails on any drift:
a renamed column, a flipped policy, or a brand-new FK that was added
without an ``ondelete`` clause. End-to-end SET NULL behaviour is
already covered by the consumer SET NULL regression tests and the
GDPR purge integration tests; the checks below are the single source
of truth for the *expected policy* matrix.
"""
from __future__ import annotations

import models  # noqa: F401  # ensure every model module is registered
from models.base import Base


# (table, column) → expected ondelete clause (upper-case).
#
# Add a new entry here whenever a model gains a ``ForeignKey('users.id')``.
# The ``test_no_user_fk_misses_ondelete`` guard below will fail loudly
# until the matrix is updated, so this list cannot silently fall behind.
_EXPECTED: dict[tuple[str, str], str] = {
    # ── SET NULL: rows that outlive the owner ──
    ("chat_messages",      "user_id"):            "SET NULL",
    ("chat_reports",       "reporter_id"):        "SET NULL",
    ("news",               "author_id"):          "SET NULL",
    ("mk_events",          "creator_user_id"):    "SET NULL",
    ("mk_event_messages",  "user_id"):            "SET NULL",
    ("watch_parties",      "host_user_id"):       "SET NULL",
    ("tickets",            "user_id"):            "SET NULL",
    ("ticket_replies",     "user_id"):            "SET NULL",
    ("media_requests",     "user_id"):            "SET NULL",
    ("media_requests",     "approved_by"):        "SET NULL",
    ("media_requests",     "requested_by_admin"): "SET NULL",
    ("request_blacklist",  "blocked_by"):         "SET NULL",
    ("featured_heroes",    "added_by"):           "SET NULL",
    ("seasonal_events",    "created_by"):         "SET NULL",
    ("user_list_items",    "added_by_user_id"):   "SET NULL",
    ("user_list_history",  "user_id"):            "SET NULL",
    ("security_blocks",    "created_by"):         "SET NULL",
    # ── CASCADE: rows that die with the owner ──
    ("user_profiles",            "user_id"): "CASCADE",
    ("user_preferences",         "user_id"): "CASCADE",
    ("user_achievements",        "user_id"): "CASCADE",
    ("user_ratings",             "user_id"): "CASCADE",
    ("user_rating_likes",        "user_id"): "CASCADE",
    ("user_lists",               "user_id"): "CASCADE",
    ("user_list_contributors",   "user_id"): "CASCADE",
    ("xp_ledger",                "user_id"): "CASCADE",
    ("seen_alerts",              "user_id"): "CASCADE",
    ("chat_mutes",               "user_id"): "CASCADE",
    ("mk_event_invitations",     "user_id"): "CASCADE",
    ("mk_notifications",         "user_id"): "CASCADE",
    ("seasonal_progress",        "user_id"): "CASCADE",
    ("watch_party_participants", "user_id"): "CASCADE",
    ("request_quotas",           "user_id"): "CASCADE",
    ("request_votes",            "user_id"): "CASCADE",
    ("release_reminders",        "user_id"): "CASCADE",
    ("news_reads",               "user_id"): "CASCADE",
}


def _iter_user_fks():
    """Yield ``(table, column, ondelete_upper, nullable)`` for every FK
    whose target column is ``users.id``."""
    for table in Base.metadata.tables.values():
        for col in table.columns:
            for fk in col.foreign_keys:
                target_table = fk.column.table.name
                target_column = fk.column.name
                if target_table == "users" and target_column == "id":
                    ondelete = (fk.ondelete or "").upper()
                    yield table.name, col.name, ondelete, col.nullable


def test_every_user_fk_matches_expected_ondelete():
    """Each FK to ``users.id`` listed in the matrix carries the right
    ``ondelete`` clause. Catches accidental policy flips on existing
    columns (e.g. a developer dropping ``ondelete=`` while editing a
    nearby attribute)."""
    seen: set[tuple[str, str]] = set()
    mismatches: list[str] = []
    for table, column, ondelete, _ in _iter_user_fks():
        seen.add((table, column))
        expected = _EXPECTED.get((table, column))
        if expected is None:
            continue
        if ondelete != expected:
            mismatches.append(
                f"{table}.{column}: expected ondelete={expected!r}, "
                f"got {ondelete!r}"
            )
    assert not mismatches, "policy drift on existing FKs:\n" + "\n".join(
        mismatches
    )

    missing_in_orm = sorted(set(_EXPECTED) - seen)
    assert not missing_in_orm, (
        "matrix lists FKs that no longer exist in the ORM (renamed or "
        f"removed?): {missing_in_orm}"
    )


def test_no_user_fk_misses_ondelete():
    """No FK to ``users.id`` may land in the schema without an explicit
    ``ondelete`` clause. The purge job raises an integrity error on
    any orphaned reference left behind by such a column, so the gate
    has to stay tight."""
    offenders = sorted(
        f"{table}.{column}"
        for table, column, ondelete, _ in _iter_user_fks()
        if not ondelete
    )
    assert not offenders, (
        "FKs to users.id missing an ondelete clause: " + ", ".join(offenders)
    )


def test_every_user_fk_is_listed_in_matrix():
    """Every FK to ``users.id`` discovered in the ORM must be present
    in ``_EXPECTED``. Catches new FKs added without updating the policy
    matrix — even if they happen to have an ``ondelete`` already."""
    unknown = sorted(
        f"{table}.{column}"
        for table, column, _, _ in _iter_user_fks()
        if (table, column) not in _EXPECTED
    )
    assert not unknown, (
        "FKs to users.id not declared in _EXPECTED — add them with the "
        f"intended policy: {unknown}"
    )


def test_user_fk_nullability_matches_policy():
    """A SET NULL FK must allow NULL in the referencing column,
    otherwise the database raises a NOT NULL violation when the parent
    row is deleted. A CASCADE FK on a user-bound row should normally be
    NOT NULL — the row makes no sense without an owner."""
    mismatches: list[str] = []
    for table, column, _, nullable in _iter_user_fks():
        expected = _EXPECTED.get((table, column))
        if expected == "SET NULL" and not nullable:
            mismatches.append(
                f"{table}.{column}: SET NULL but column is NOT NULL"
            )
        elif expected == "CASCADE" and nullable:
            mismatches.append(
                f"{table}.{column}: CASCADE but column is nullable"
            )
    assert not mismatches, "nullability/policy mismatch:\n" + "\n".join(
        mismatches
    )
