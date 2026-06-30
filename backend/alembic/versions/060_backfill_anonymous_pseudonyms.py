"""Backfill anonymized pseudonyms for users who never picked one.

Imported Emby accounts used to store their raw Emby login in
``user_profiles.display_name``. The privacy boundary now generates a
stable ``Renard-Bleu-42`` pseudo for every silent account (see
``services.portal._pseudo_words``), but already-imported users still carry
their login in ``display_name`` — which would leak the moment they confirm
the first-login modal. This data migration overwrites it with the
generated pseudo for every account that never picked a pseudo
(``display_name_must_set`` set), leaving the administrator and users with a
chosen pseudo untouched.

The French pseudo is stored as the canonical value; user-facing surfaces
re-localize it per viewer. Irreversible — the original logins are
intentionally discarded, so ``downgrade`` is a no-op. ``generate_pseudo`` is
imported only when there are rows to backfill, so a fresh install (which has
no imported users at migration time) never couples to app code.
"""
from alembic import op
import sqlalchemy as sa


revision = "060_backfill_anonymous_pseudonyms"
down_revision = "059_index_pending_deletion_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.text(
        "SELECT user_id FROM user_profiles "
        "WHERE display_name_must_set AND (role IS NULL OR role <> 'admin')"
    )).fetchall()
    if not rows:
        return

    from services.portal._pseudo_words import generate_pseudo

    update = sa.text(
        "UPDATE user_profiles SET display_name = :dn WHERE user_id = :uid"
    )
    for (user_id,) in rows:
        bind.execute(update, {"dn": generate_pseudo(user_id, "fr"), "uid": user_id})


def downgrade() -> None:
    # Irreversible: the original Emby logins were intentionally discarded.
    pass
