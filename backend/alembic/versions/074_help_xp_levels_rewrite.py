"""Rewrite the XP and levels help articles the admin never edited

« Comment gagner de l'XP ? » still gave the former watch XP rule (10 XP a movie,
3 an episode, at 85 % of its length), and « Les paliers et les grades » mixed
the level titles up and said a rank is never lost. As 071 did, this rewrites
the French text of each of the two articles that still holds its starter title
and text, whatever its slug became: same words, tags, links and pictures,
spacing and entity spelling aside. Its English text is rewritten too while it
is still the English starter. An article whose French the admin retouched, or
that sits in the trash, is left alone, its English too.
``sanitize_html`` is imported only when one of the two articles exists, so a
fresh install never couples to app code. Offline (``--sql``) it renders nothing:
finding the untouched articles needs the rows. Irreversible on purpose:
``downgrade`` is a no-op, the new text being right for the older code too.

Revision ID: 074_help_xp_levels_rewrite
Revises: 073_completion_exclusive_seconds
Create Date: 2026-11-22
"""
import html

import sqlalchemy as sa
from alembic import context, op

revision = "074_help_xp_levels_rewrite"
down_revision = "073_completion_exclusive_seconds"
branch_labels = None
depends_on = None

_XP_FR_OLD = """
<p>L'<strong>XP</strong> (points d'expérience) fait monter ton <strong>niveau</strong>, jusqu'au niveau 50. Ta barre d'XP et ton niveau sont sur <strong>« Mon profil »</strong>.</p>
<p><strong>Ce qui rapporte de l'XP :</strong></p>
<ul>
  <li><strong>+10 XP</strong> par film regardé sur Emby jusqu'à au moins 85 % de sa durée.</li>
  <li><strong>+3 XP</strong> par épisode regardé jusqu'à au moins 85 % de sa durée.</li>
  <li><strong>+2 XP</strong> quand tu te connectes au portail, une fois par jour.</li>
  <li><strong>+5 XP</strong> par nouvelle demande, jusqu'à 25 XP par jour.</li>
  <li><strong>Les trophées</strong> : chacun rapporte son XP une seule fois, quand tu le débloques. Le montant s'affiche dans <strong>« Voir tous les trophées »</strong>, sur <strong>« Mon profil »</strong>.</li>
</ul>
<p>Revoir le même film ou le même épisode dans les 24 heures ne rapporte rien de plus. Les autres actions (créer un événement ou une liste publique, écrire dans le chat…) ne donnent pas d'XP directement, mais font avancer certains trophées.</p>
<p><strong>Périodes bonus :</strong> l'administrateur peut lancer une période pendant laquelle l'XP gagnée est multipliée.</p>
"""

_XP_FR_NEW = """
<p>L'<strong>XP</strong> (points d'expérience) fait monter ton <strong>niveau</strong>, jusqu'au niveau 50. Ta barre d'XP et ton niveau sont sur <strong>« Mon profil »</strong>.</p>
<p><strong>Ce qui rapporte de l'XP :</strong></p>
<ul>
  <li><strong>+20 XP par heure</strong> de film ou d'épisode vu en entier : la fin atteinte et au moins les trois quarts de sa durée vraiment regardés. Un film de 2 h rapporte 40 XP, un épisode de 45 min 15 XP.</li>
  <li><strong>+2 XP</strong> quand tu te connectes au portail, une fois par jour.</li>
  <li><strong>+5 XP</strong> par nouvelle demande, jusqu'à 25 XP par jour.</li>
  <li><strong>Les trophées</strong> : chacun rapporte son XP une seule fois, quand tu le débloques. Le montant s'affiche dans <strong>« Voir tous les trophées »</strong>, sur <strong>« Mon profil »</strong>.</li>
</ul>
<p><strong>Ne rapportent rien :</strong> revoir le même titre dans les 24 heures, un titre laissé en pause ou passé en avance rapide, un titre lu en même temps qu'un autre sur ton compte. Un lecteur qui n'indique pas où il en est (certains lecteurs de fichiers) ne rapporte pas d'XP de visionnage. Les autres actions (créer un événement ou une liste publique, écrire dans le chat…) ne donnent pas d'XP, mais font avancer certains trophées.</p>
<p><strong>Périodes bonus :</strong> l'administrateur peut lancer une période pendant laquelle l'XP gagnée est multipliée.</p>
"""

_XP_EN_OLD = """
<p><strong>XP</strong> (experience points) raises your <strong>level</strong>, up to level 50. Your XP bar and your level are on <strong>“My profile”</strong>.</p>
<p><strong>What earns XP:</strong></p>
<ul>
  <li><strong>+10 XP</strong> per movie watched on Emby through at least 85% of its length.</li>
  <li><strong>+3 XP</strong> per episode watched through at least 85% of its length.</li>
  <li><strong>+2 XP</strong> when you sign in to the portal, once a day.</li>
  <li><strong>+5 XP</strong> per new request, up to 25 XP a day.</li>
  <li><strong>Trophies</strong>: each one gives its XP only once, when you unlock it. The amount shows in <strong>“See all trophies”</strong>, on <strong>“My profile”</strong>.</li>
</ul>
<p>Watching the same movie or episode again within 24 hours gives nothing more. Other actions (creating an event or a public list, writing in the chat…) give no XP directly, but they move some trophies forward.</p>
<p><strong>Bonus periods:</strong> the administrator can start a period during which the XP you earn is multiplied.</p>
"""

_XP_EN_NEW = """
<p><strong>XP</strong> (experience points) raises your <strong>level</strong>, up to level 50. Your XP bar and your level are on <strong>“My profile”</strong>.</p>
<p><strong>What earns XP:</strong></p>
<ul>
  <li><strong>+20 XP per hour</strong> of a movie or episode watched to the end: the end reached and at least three quarters of its length really watched. A 2-hour movie gives 40 XP, a 45-minute episode 15 XP.</li>
  <li><strong>+2 XP</strong> when you sign in to the portal, once a day.</li>
  <li><strong>+5 XP</strong> per new request, up to 25 XP a day.</li>
  <li><strong>Trophies</strong>: each one gives its XP only once, when you unlock it. The amount shows in <strong>“See all trophies”</strong>, on <strong>“My profile”</strong>.</li>
</ul>
<p><strong>What gives nothing:</strong> watching the same title again within 24 hours, a title left paused or fast-forwarded, a title played at the same time as another one on your account. A player that does not report where it is (some file players) gives no watch XP. Other actions (creating an event or a public list, writing in the chat…) give no XP, but they move some trophies forward.</p>
<p><strong>Bonus periods:</strong> the administrator can start a period during which the XP you earn is multiplied.</p>
"""

_LEVELS_FR_OLD = """
<p>Chaque niveau t'attribue un <strong>grade</strong>, et chaque grade ouvre un palier visuel : couleur de bordure, halo de la carte, particules autour de l'avatar, titre affiché à côté du pseudo.</p>
<table>
  <thead>
    <tr><th>Niveaux</th><th>Grade</th><th>Titre</th></tr>
  </thead>
  <tbody>
    <tr><td>1 → 5</td><td>Bronze</td><td>Spectateur / Amateur</td></tr>
    <tr><td>6 → 10</td><td>Argent</td><td>Régulier</td></tr>
    <tr><td>11 → 19</td><td>Or</td><td>Passionné</td></tr>
    <tr><td>20 → 29</td><td>Platine</td><td>Expert</td></tr>
    <tr><td>30 → 39</td><td>Diamant</td><td>Maître</td></tr>
    <tr><td>40 → 49</td><td>Maître</td><td>Maître</td></tr>
    <tr><td>50</td><td>Légendaire</td><td>Légende</td></tr>
  </tbody>
</table>
<p>La progression suit une courbe de plus en plus exigeante : passer du niveau 1 au 2 demande peu d'XP, mais atteindre le niveau 50 (la <em>Légende</em>) prend des mois d'activité régulière.</p>
<p>Le grade est <strong>permanent</strong> : tu ne peux pas le perdre. Seul un administrateur peut, en cas d'erreur, ajuster manuellement ton niveau depuis le panneau de débogage.</p>
"""

_LEVELS_FR_NEW = """
<p>Chaque niveau t'attribue un <strong>grade</strong> et un <strong>titre</strong>. Le grade change le style de ta carte : couleur de bordure, halo, particules autour de l'avatar. Le titre s'affiche à côté de ton pseudo.</p>
<table>
  <thead>
    <tr><th>Niveaux</th><th>Grade</th><th>Titre</th></tr>
  </thead>
  <tbody>
    <tr><td>1 → 2</td><td>Bronze</td><td>Spectateur</td></tr>
    <tr><td>3 → 5</td><td>Bronze</td><td>Amateur</td></tr>
    <tr><td>6 → 10</td><td>Argent</td><td>Habitué</td></tr>
    <tr><td>11</td><td>Or</td><td>Habitué</td></tr>
    <tr><td>12 → 19</td><td>Or</td><td>Passionné</td></tr>
    <tr><td>20 → 29</td><td>Platine</td><td>Expert</td></tr>
    <tr><td>30 → 39</td><td>Diamant</td><td>Maître</td></tr>
    <tr><td>40 → 49</td><td>Maître</td><td>Maître</td></tr>
    <tr><td>50</td><td>Légendaire</td><td>Légende</td></tr>
  </tbody>
</table>
<p>Chaque niveau demande plus d'XP que le précédent. Le niveau 50, la <em>Légende</em>, demande 127 500 XP : plus d'un an, même pour un très gros spectateur.</p>
<p>Ton niveau suit ton XP : il peut baisser si de l'XP t'est retirée, par exemple quand un trophée gagné par erreur est retiré.</p>
"""

_LEVELS_EN_OLD = """
<p>Each level gives you a <strong>rank</strong>, and each rank opens a visual tier: border color, card glow, particles around the avatar, title shown next to your username.</p>
<table>
  <thead>
    <tr><th>Levels</th><th>Rank</th><th>Title</th></tr>
  </thead>
  <tbody>
    <tr><td>1 → 5</td><td>Bronze</td><td>Spectator / Amateur</td></tr>
    <tr><td>6 → 10</td><td>Silver</td><td>Regular</td></tr>
    <tr><td>11 → 19</td><td>Gold</td><td>Passionate</td></tr>
    <tr><td>20 → 29</td><td>Platinum</td><td>Expert</td></tr>
    <tr><td>30 → 39</td><td>Diamond</td><td>Master</td></tr>
    <tr><td>40 → 49</td><td>Master</td><td>Master</td></tr>
    <tr><td>50</td><td>Legendary</td><td>Legend</td></tr>
  </tbody>
</table>
<p>Progress follows an increasingly demanding curve: going from level 1 to 2 takes little XP, but reaching level 50 (the <em>Legend</em>) takes months of regular activity.</p>
<p>Your rank is <strong>permanent</strong>: you cannot lose it. Only an administrator can adjust your level by hand from the debug panel, to fix a mistake.</p>
"""

_LEVELS_EN_NEW = """
<p>Each level gives you a <strong>rank</strong> and a <strong>title</strong>. The rank changes the style of your card: border color, glow, particles around the avatar. The title shows next to your username.</p>
<table>
  <thead>
    <tr><th>Levels</th><th>Rank</th><th>Title</th></tr>
  </thead>
  <tbody>
    <tr><td>1 → 2</td><td>Bronze</td><td>Spectator</td></tr>
    <tr><td>3 → 5</td><td>Bronze</td><td>Amateur</td></tr>
    <tr><td>6 → 10</td><td>Silver</td><td>Regular</td></tr>
    <tr><td>11</td><td>Gold</td><td>Regular</td></tr>
    <tr><td>12 → 19</td><td>Gold</td><td>Passionate</td></tr>
    <tr><td>20 → 29</td><td>Platinum</td><td>Expert</td></tr>
    <tr><td>30 → 39</td><td>Diamond</td><td>Master</td></tr>
    <tr><td>40 → 49</td><td>Master</td><td>Master</td></tr>
    <tr><td>50</td><td>Legendary</td><td>Legend</td></tr>
  </tbody>
</table>
<p>Each level takes more XP than the one before. Level 50, the <em>Legend</em>, takes 127,500 XP: more than a year, even for a very heavy viewer.</p>
<p>Your level follows your XP: it can go down if XP is taken from you, for instance when a trophy earned by mistake is removed.</p>
"""

# slug -> lang -> (starter text, its rewrite)
REWRITES = {
    "comment-gagner-de-l-xp": {"fr": (_XP_FR_OLD, _XP_FR_NEW), "en": (_XP_EN_OLD, _XP_EN_NEW)},
    "les-paliers-et-grades": {"fr": (_LEVELS_FR_OLD, _LEVELS_FR_NEW), "en": (_LEVELS_EN_OLD, _LEVELS_EN_NEW)},
}
# slug -> lang -> starter title (unchanged by the rewrite)
TITLES = {
    "comment-gagner-de-l-xp": {"fr": "Comment gagner de l'XP ?", "en": "How do I earn XP?"},
    "les-paliers-et-grades": {"fr": "Les paliers et les grades", "en": "Tiers and ranks"},
}


def shape(body: str | None) -> str:
    """Tags, links and words of a body, its spacing and entity spelling aside."""
    spaced = html.unescape(body or "").replace("<", " <").replace(">", "> ")
    return " ".join(spaced.split())


def _rewrite(bind, row_id: int, body: str) -> None:
    bind.execute(
        sa.text(
            "UPDATE help_article_translations "
            "SET body_html = :body, updated_at = CURRENT_TIMESTAMP WHERE id = :id"
        ),
        {"body": body, "id": row_id},
    )


def upgrade() -> None:
    if context.is_offline_mode():
        return
    bind = op.get_bind()
    # Found by its starter title, not its slug: an older editor save could move a
    # starter article's slug without touching a word of it.
    by_title = {titles["fr"]: slug for slug, titles in TITLES.items()}
    rows = bind.execute(
        sa.text(
            "SELECT t.id, t.article_id, t.title, t.body_html FROM help_article_translations t "
            "JOIN help_articles a ON a.id = t.article_id "
            "WHERE t.lang = 'fr' AND a.deleted_at IS NULL AND t.title IN :titles"
        ).bindparams(sa.bindparam("titles", expanding=True)),
        {"titles": list(by_title)},
    ).fetchall()
    if not rows:
        return

    from services.portal.help_sanitize import sanitize_html

    def seeded(slug: str, lang: str, which: int) -> str:
        return sanitize_html(REWRITES[slug][lang][which].strip())

    for row_id, article_id, title, body in rows:
        slug = by_title[title]
        if shape(body) != shape(seeded(slug, "fr", 0)):
            continue
        _rewrite(bind, row_id, seeded(slug, "fr", 1))
        english = bind.execute(
            sa.text(
                "SELECT id, title, body_html FROM help_article_translations "
                "WHERE article_id = :article AND lang = 'en'"
            ),
            {"article": article_id},
        ).first()
        if (
            english is not None
            and english.title == TITLES[slug]["en"]
            and shape(english.body_html) == shape(seeded(slug, "en", 0))
        ):
            _rewrite(bind, english.id, seeded(slug, "en", 1))


def downgrade() -> None:
    # Irreversible on purpose: the new text is right for the older code too.
    pass
