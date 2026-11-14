"""Compare display names by what they read as, and keep each one to one member

Adds ``user_profiles.display_name_key`` (the name whatever its case, width,
composition or invisible marks; unique) and ``display_name_skeleton`` (what it
reads as, look-alike letters folded; indexed). Both are filled for each member
who chose a name; admins and members who still owe one keep them empty.

Existing names are sorted out first, with the app's own rules. A chosen name
that is invalid, reserved or shaped like a provisional pseudo, or that a member
chose earlier (same key, or same skeleton), goes back to « must choose »: its
holder picks a new one at the next visit and shows a provisional pseudo until
then. A member who still owes a name and never had one gets the provisional
pseudo stored instead of the sign-in name. The rules are imported only when a
profile exists, so a fresh install never couples to app code.

The PostgreSQL index on ``LOWER(display_name)`` (migration 031) goes: it held
every stored name, provisional pseudos and admin sign-in names included, so two
accounts could not share a provisional pseudo and an admin's sign-in name stayed
guessable. The unique key replaces it, for chosen names only. Downgrade drops
the two columns and puts that index back; the names sent back to « must
choose » stay so.

Revision ID: 072_display_name_keys
Revises: 071_help_seed_rewrite
Create Date: 2026-11-13
"""
import sqlalchemy as sa
from alembic import op

revision = "072_display_name_keys"
down_revision = "071_help_seed_rewrite"
branch_labels = None
depends_on = None

_TABLE = "user_profiles"
_KEY, _SKELETON = "display_name_key", "display_name_skeleton"
KEY_INDEX = "uq_user_profiles_display_name_key"
SKELETON_INDEX = "ix_user_profiles_display_name_skeleton"
LOWER_INDEX = "ix_user_profiles_display_name_lower"  # PostgreSQL only, from 031
_ADMIN = "admin"


def _columns() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(_TABLE)}


def _indexes() -> set[str]:
    return {i["name"] for i in sa.inspect(op.get_bind()).get_indexes(_TABLE)}


def sort_names(rows: list) -> tuple[dict[int, tuple[str, str | None]], set[int], dict[int, str]]:
    """Split profiles ``(id, user_id, name, must_set, role, changed_at)`` into the
    keys to store per id, the ids sent back to « must choose », and the provisional
    pseudos to store per id. Earliest chosen keeps a shared name; an unknown date
    counts as earliest, then the oldest profile."""
    from services.portal._pseudo_words import generate_pseudo
    from services.portal.display_name_rules import is_reserved_display_name, looks_provisional
    from services.portal.display_name_text import (
        display_name_key,
        display_name_skeleton,
        has_ink,
        hides_text,
    )

    keys: dict[int, tuple[str, str | None]] = {}
    reset: set[int] = set()
    placeholders: dict[int, str] = {}
    chosen = []
    for pid, user_id, name, must_set, role, changed_at in rows:
        if role == _ADMIN:
            continue
        if must_set:
            if changed_at is None:
                placeholders[pid] = generate_pseudo(user_id, "fr")
            continue
        name = name or ""
        if hides_text(name) or not has_ink(name) or is_reserved_display_name(name) or looks_provisional(name):
            reset.add(pid)
            continue
        chosen.append((changed_at is not None, changed_at or 0, pid, name))
    seen_keys: set[str] = set()
    seen_skeletons: set[str] = set()
    for _, _, pid, name in sorted(chosen, key=lambda c: (c[0], str(c[1]), c[2])):
        key, skeleton = display_name_key(name), display_name_skeleton(name)
        if key in seen_keys or (skeleton and skeleton in seen_skeletons):
            reset.add(pid)
            continue
        seen_keys.add(key)
        if skeleton:
            seen_skeletons.add(skeleton)
        keys[pid] = (key, skeleton or None)
    return keys, reset, placeholders


def upgrade() -> None:
    columns = _columns()
    for column in (_KEY, _SKELETON):
        if column not in columns:
            op.add_column(_TABLE, sa.Column(column, sa.Text(), nullable=True))
    if LOWER_INDEX in _indexes():
        op.drop_index(LOWER_INDEX, table_name=_TABLE)

    bind = op.get_bind()
    rows = bind.execute(sa.text(
        "SELECT id, user_id, display_name, display_name_must_set, role, display_name_changed_at "
        "FROM user_profiles ORDER BY id"
    )).fetchall()
    if rows:
        keys, reset, placeholders = sort_names([tuple(r) for r in rows])
        bind.execute(sa.text(
            "UPDATE user_profiles SET display_name_key = NULL, display_name_skeleton = NULL"
        ))
        for pid in sorted(reset):
            bind.execute(
                sa.text("UPDATE user_profiles SET display_name_must_set = :flag WHERE id = :id"),
                {"flag": True, "id": pid},
            )
        for pid, name in placeholders.items():
            bind.execute(
                sa.text("UPDATE user_profiles SET display_name = :name WHERE id = :id"),
                {"name": name, "id": pid},
            )
        for pid, (key, skeleton) in keys.items():
            bind.execute(
                sa.text(
                    "UPDATE user_profiles SET display_name_key = :key, "
                    "display_name_skeleton = :skeleton WHERE id = :id"
                ),
                {"key": key, "skeleton": skeleton, "id": pid},
            )

    indexes = _indexes()
    if KEY_INDEX not in indexes:
        op.create_index(KEY_INDEX, _TABLE, [_KEY], unique=True)
    if SKELETON_INDEX not in indexes:
        op.create_index(SKELETON_INDEX, _TABLE, [_SKELETON])


def downgrade() -> None:
    indexes = _indexes()
    for index in (KEY_INDEX, SKELETON_INDEX):
        if index in indexes:
            op.drop_index(index, table_name=_TABLE)
    columns = _columns()
    for column in (_KEY, _SKELETON):
        if column in columns:
            op.drop_column(_TABLE, column)
    # As 031 made it; stops the downgrade if two stored names now differ only by case.
    if op.get_bind().dialect.name == "postgresql" and LOWER_INDEX not in indexes:
        op.create_index(LOWER_INDEX, _TABLE, [sa.text("LOWER(display_name)")], unique=True)
