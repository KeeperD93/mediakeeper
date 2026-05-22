"""GDPR groundwork: ``users`` deletion timestamps, chat FK SET NULL,
broken FKs fixed, opt-in privacy settings inserted.

This migration prepares the schema for the opt-in GDPR opt-in GDPR
mode without exposing any user-facing surface yet:

* Adds ``users.deletion_requested_at`` and ``users.pending_deletion_at``
  so the upcoming self-service deletion flow has a place to record the
  request and the grace-period deadline.

* Re-creates the ``chat_messages.user_id`` FK with ``ON DELETE
  SET NULL`` and makes the column nullable. When a future GDPR purge
  hard-deletes a ``users`` row, the messages survive with a NULL
  author so the surrounding conversation stays intact.

* Adds ``ON DELETE CASCADE`` to ``seen_alerts.user_id`` and
  ``xp_ledger.user_id``. Both columns previously had no ``ondelete``
  clause, which would force the database to refuse a hard ``DELETE
  FROM users`` once the purge job is wired in.

* Inserts five ``gdpr.*`` rows in the ``settings`` table with
  disabling defaults: ``gdpr.enabled=false``, two preset HTML privacy
  texts (FR/EN), an empty ``gdpr.dpo_contact``, and a 30-day default
  for ``gdpr.account_purge_delay_days``. The opt-in GDPR UI reads these
  rows; until the toggle is flipped they have no runtime effect.

The downgrade is symmetric. SQLite-friendly via ``op.batch_alter_table``.
"""
from alembic import op
import sqlalchemy as sa


revision = "040_gdpr_pending_deletion"
down_revision = "039_users_tokens_invalidated_at"
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# Preset privacy texts (admin overrides via the opt-in GDPR settings UI).
# Kept here so the migration is self-contained and a fresh DB starts with a
# usable opt-in default.
# ---------------------------------------------------------------------------

_PRIVACY_TEXT_FR = """\
<h2>Politique de confidentialité</h2>
<p>Cette instance MediaKeeper est hébergée et administrée par <strong>[NOM DE L'ADMINISTRATEUR — à compléter]</strong>. L'administrateur agit en tant que responsable de traitement.</p>
<h3>Données collectées</h3>
<ul>
  <li>Identifiant et avatar Emby (synchronisés depuis votre compte Emby)</li>
  <li>Listes de visionnage et demandes de médias que vous créez</li>
  <li>Messages de chat</li>
  <li>Succès débloqués et progression</li>
  <li>Préférences d'affichage (langue, thème, notifications)</li>
  <li>Journaux d'authentification (date, dernière connexion)</li>
</ul>
<h3>Finalités</h3>
<p>Ces données servent uniquement au fonctionnement du service : recommandations, suivi de vos demandes, modération du chat, notifications. Elles ne sont jamais revendues ni partagées avec des tiers, à l'exception des notifications Discord configurées par l'administrateur.</p>
<h3>Durée de conservation</h3>
<p>Vos données sont conservées tant que votre compte est actif. À la suppression du compte, les données vous identifiant sont effacées dans un délai défini par l'administrateur. Vos messages de chat sont anonymisés, pas effacés, pour préserver l'intégrité des conversations des autres utilisateurs.</p>
<h3>Sécurité</h3>
<p>Les données sont stockées sur un serveur opéré par l'administrateur. Les valeurs sensibles (clés API, mots de passe) sont chiffrées au repos. Aucun cookie publicitaire, aucun tracker tiers, aucune télémétrie.</p>
<h3>Modification de cette politique</h3>
<p>L'administrateur peut modifier cette politique à tout moment.</p>"""


_PRIVACY_TEXT_EN = """\
<h2>Privacy policy</h2>
<p>This MediaKeeper instance is hosted and administered by <strong>[ADMINISTRATOR NAME — to be filled in]</strong>. The administrator acts as the data controller.</p>
<h3>Data collected</h3>
<ul>
  <li>Emby identifier and avatar (synchronized from your Emby account)</li>
  <li>Watchlists and media requests you create</li>
  <li>Chat messages</li>
  <li>Unlocked achievements and progress</li>
  <li>Display preferences (language, theme, notifications)</li>
  <li>Authentication logs (date, last login)</li>
</ul>
<h3>Purposes</h3>
<p>This data is used solely to operate the service: recommendations, request tracking, chat moderation, notifications. It is never sold or shared with third parties, except for Discord notifications configured by the administrator.</p>
<h3>Retention</h3>
<p>Your data is retained as long as your account is active. Upon account deletion, identifying data is erased within a delay set by the administrator. Chat messages are anonymized, not erased, to preserve the integrity of other users' conversations.</p>
<h3>Security</h3>
<p>Data is stored on a server operated by the administrator. Sensitive values (API keys, passwords) are encrypted at rest. No advertising cookies, no third-party trackers, no telemetry.</p>
<h3>Changes to this policy</h3>
<p>The administrator may update this policy at any time.</p>"""


_GDPR_SETTINGS = (
    ("gdpr.enabled", "false"),
    ("gdpr.privacy_text_fr", _PRIVACY_TEXT_FR),
    ("gdpr.privacy_text_en", _PRIVACY_TEXT_EN),
    ("gdpr.dpo_contact", ""),
    ("gdpr.account_purge_delay_days", "30"),
)


def _user_fk_name(inspector, table: str, column: str) -> str | None:
    for fk in inspector.get_foreign_keys(table):
        if column in fk.get("constrained_columns", []):
            return fk.get("name")
    return None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1) ``users`` deletion timestamps -------------------------------------
    user_cols = {c["name"] for c in inspector.get_columns("users")}
    if "deletion_requested_at" not in user_cols:
        op.add_column(
            "users",
            sa.Column("deletion_requested_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "pending_deletion_at" not in user_cols:
        op.add_column(
            "users",
            sa.Column("pending_deletion_at", sa.DateTime(timezone=True), nullable=True),
        )

    # 2) ``chat_messages.user_id`` → nullable + ON DELETE SET NULL --------
    chat_fk_name = _user_fk_name(inspector, "chat_messages", "user_id")
    with op.batch_alter_table("chat_messages") as batch_op:
        batch_op.alter_column(
            "user_id", existing_type=sa.Integer(), nullable=True
        )
        if chat_fk_name:
            batch_op.drop_constraint(chat_fk_name, type_="foreignkey")
        batch_op.create_foreign_key(
            "chat_messages_user_id_fkey",
            "users",
            ["user_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # 3) ``seen_alerts.user_id`` → ON DELETE CASCADE (was missing) -------
    seen_fk_name = _user_fk_name(inspector, "seen_alerts", "user_id")
    with op.batch_alter_table("seen_alerts") as batch_op:
        if seen_fk_name:
            batch_op.drop_constraint(seen_fk_name, type_="foreignkey")
        batch_op.create_foreign_key(
            "seen_alerts_user_id_fkey",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )

    # 4) ``xp_ledger.user_id`` → ON DELETE CASCADE (was missing) ---------
    xp_fk_name = _user_fk_name(inspector, "xp_ledger", "user_id")
    with op.batch_alter_table("xp_ledger") as batch_op:
        if xp_fk_name:
            batch_op.drop_constraint(xp_fk_name, type_="foreignkey")
        batch_op.create_foreign_key(
            "xp_ledger_user_id_fkey",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )

    # 5) Insert opt-in GDPR settings (idempotent) ------------------------
    settings = sa.table(
        "settings",
        sa.column("key", sa.String),
        sa.column("value", sa.Text),
    )
    existing_keys = {
        row[0]
        for row in bind.execute(
            sa.select(settings.c.key).where(settings.c.key.like("gdpr.%"))
        ).fetchall()
    }
    rows = [
        {"key": key, "value": value}
        for key, value in _GDPR_SETTINGS
        if key not in existing_keys
    ]
    if rows:
        op.bulk_insert(settings, rows)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1) Remove inserted settings ----------------------------------------
    settings = sa.table(
        "settings",
        sa.column("key", sa.String),
    )
    bind.execute(
        sa.delete(settings).where(settings.c.key.like("gdpr.%"))
    )

    # 2) Revert ``xp_ledger.user_id`` (drop ondelete) --------------------
    xp_fk_name = _user_fk_name(inspector, "xp_ledger", "user_id")
    with op.batch_alter_table("xp_ledger") as batch_op:
        if xp_fk_name:
            batch_op.drop_constraint(xp_fk_name, type_="foreignkey")
        batch_op.create_foreign_key(
            "xp_ledger_user_id_fkey",
            "users",
            ["user_id"],
            ["id"],
        )

    # 3) Revert ``seen_alerts.user_id`` (drop ondelete) ------------------
    seen_fk_name = _user_fk_name(inspector, "seen_alerts", "user_id")
    with op.batch_alter_table("seen_alerts") as batch_op:
        if seen_fk_name:
            batch_op.drop_constraint(seen_fk_name, type_="foreignkey")
        batch_op.create_foreign_key(
            "seen_alerts_user_id_fkey",
            "users",
            ["user_id"],
            ["id"],
        )

    # 4) Revert ``chat_messages.user_id`` to CASCADE + NOT NULL ---------
    # Backfill any NULL ``user_id`` left by purges (pre-1.0 only — the
    # production data is wiped at v1.0). The placeholder ``-1`` keeps the
    # NOT NULL constraint satisfiable while making the row obviously
    # synthetic if it ever reaches a query.
    chat_messages = sa.table(
        "chat_messages",
        sa.column("user_id", sa.Integer),
    )
    bind.execute(
        sa.update(chat_messages)
        .where(chat_messages.c.user_id.is_(None))
        .values(user_id=-1)
    )
    chat_fk_name = _user_fk_name(inspector, "chat_messages", "user_id")
    with op.batch_alter_table("chat_messages") as batch_op:
        if chat_fk_name:
            batch_op.drop_constraint(chat_fk_name, type_="foreignkey")
        batch_op.create_foreign_key(
            "chat_messages_user_id_fkey",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.alter_column(
            "user_id", existing_type=sa.Integer(), nullable=False
        )

    # 5) Drop the deletion timestamps from ``users`` --------------------
    user_cols = {c["name"] for c in inspector.get_columns("users")}
    if "pending_deletion_at" in user_cols:
        op.drop_column("users", "pending_deletion_at")
    if "deletion_requested_at" in user_cols:
        op.drop_column("users", "deletion_requested_at")
