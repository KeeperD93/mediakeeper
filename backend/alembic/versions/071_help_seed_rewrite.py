"""Rewrite six starter help articles the admin never edited

« Comment faire une demande ? » sent members to the Requests tab, which only
admins see, « Choisir son pseudo » gave the old name rules, and the request
quotas, XP, leaderboard and events articles described rules the portal never
had. The starter text only reaches new installs (the seed never overwrites an
article), so this rewrites the French text of each of the six articles that
still holds its original title and text, whatever its slug became: same words,
tags, links and pictures, spacing and entity spelling aside. An article the admin retouched, even by one picture, or
put in the trash, is left alone.
``sanitize_html`` is imported only when one of the two articles exists, so a
fresh install never couples to app code. Irreversible on purpose: ``downgrade`` is a
no-op, the new text being right for the older code too.

Revision ID: 071_help_seed_rewrite
Revises: 070_profile_onboarding
Create Date: 2026-11-13
"""
import html

import sqlalchemy as sa
from alembic import op

revision = "071_help_seed_rewrite"
down_revision = "070_profile_onboarding"
branch_labels = None
depends_on = None

_REQUEST_OLD = """
<p>MediaKeeper te permet de demander un film ou une série qui n'est pas encore disponible sur la plateforme. La procédure tient en quelques étapes :</p>
<ol>
  <li>Ouvre l'onglet <strong>Demandes</strong> depuis la barre du haut.</li>
  <li>Clique sur le bouton <strong>« Nouvelle demande »</strong>.</li>
  <li>Recherche le titre via la barre de recherche : MediaKeeper interroge directement TMDB pour t'éviter les fautes d'orthographe.</li>
  <li>Choisis la fiche correcte dans les résultats (vérifie l'année et l'affiche).</li>
  <li>Ajoute un commentaire si tu veux préciser une saison, un format, ou une raison particulière.</li>
  <li>Valide. Ta demande passe automatiquement en statut <em>« En attente »</em>.</li>
</ol>
<p>Une fois validée par l'administrateur, ta demande est ajoutée à la file de téléchargement et tu reçois une notification dès que le contenu est disponible sur Emby.</p>
<p><strong>Astuce :</strong> avant de demander, vérifie toujours que le titre n'est pas déjà disponible via la barre de recherche du portail.</p>
"""

_REQUEST_NEW = """
<p>MediaKeeper te permet de demander un film ou une série qui n'est pas encore dans la bibliothèque. Tout se fait depuis la page d'accueil ou la recherche :</p>
<ol>
  <li>Sur la <strong>page d'accueil</strong>, un titre mis en avant se demande directement avec le bouton <strong>« Demander »</strong>.</li>
  <li>Sinon, tape son nom dans <strong>« Rechercher »</strong>, en haut (la loupe sur téléphone), puis choisis une suggestion ou parcours les résultats.</li>
  <li>Ouvre la fiche du titre et touche <strong>« Demander »</strong>. À la souris, le bouton apparaît aussi sur l'affiche, dans les résultats.</li>
  <li>Dans la fenêtre <strong>« Faire une demande »</strong>, valide. Pour une série, coche d'abord les saisons voulues.</li>
</ol>
<p>Le titre passe à <em>« Demandé »</em>. Une fois la demande approuvée et le titre ajouté, la cloche des notifications te prévient qu'il est disponible.</p>
"""

_NAME_OLD = """
<p>À ta première connexion sur le portail, MediaKeeper te demande de <strong>choisir un pseudo</strong>. Quelques règles à connaître :</p>
<ul>
  <li>Le pseudo doit être <strong>unique</strong> sur la plateforme (insensible à la casse : « Lola » et « lola » sont identiques).</li>
  <li>Longueur entre 2 et 50 caractères. Lettres, chiffres, espaces, tirets et apostrophes acceptés.</li>
  <li>Certains noms sont <strong>réservés</strong> et refusés : <em>admin, administrator, administrateur, root</em>.</li>
  <li>Si le pseudo est déjà pris, MediaKeeper te propose <strong>jusqu'à 5 suggestions</strong> libres (avec un suffixe numérique).</li>
</ul>
<p><strong>Verrouillage 6 mois</strong> : une fois ton pseudo choisi ou modifié, tu ne peux pas en changer pendant <strong>180 jours</strong>. C'est volontaire pour éviter l'usurpation et garantir aux autres utilisateurs qu'un nom = une personne stable.</p>
<p>Les administrateurs peuvent bypasser le verrou si tu as une vraie raison de changer (faute de frappe, incident).</p>
"""

_NAME_NEW = """
<p>À ta première connexion sur le portail, MediaKeeper te demande de <strong>choisir un pseudo</strong>. En attendant, les autres membres voient un pseudo provisoire tiré au hasard (« Renard-Bleu-42 ») : il ne peut pas être gardé. Quelques règles à connaître :</p>
<ul>
  <li>Le pseudo doit être <strong>unique</strong> sur la plateforme (insensible à la casse : « Lola » et « lola » sont identiques).</li>
  <li>Longueur entre 3 et 50 caractères (2 suffisent en chinois ou en coréen). Pour le minimum, seuls comptent les lettres, les chiffres et les symboles.</li>
  <li>Certains noms sont <strong>réservés</strong> et refusés, ainsi que leurs imitations et les pseudos où on les lit comme un mot (<em>SuperAdmin</em>, <em>Joe Root</em>) : <em>admin, administrator, administrateur, root</em>.</li>
  <li>Si le pseudo est déjà pris, MediaKeeper te propose <strong>jusqu'à 5 suggestions</strong> libres (avec un suffixe numérique).</li>
  <li>Si un administrateur réinitialise ton pseudo, choisis-en un nouveau : l'ancien n'est plus accepté.</li>
</ul>
<p><strong>Verrouillage 6 mois</strong> : une fois ton pseudo choisi ou modifié, tu ne peux pas en changer pendant <strong>180 jours</strong>. C'est volontaire pour éviter l'usurpation et garantir aux autres utilisateurs qu'un nom = une personne stable.</p>
<p>Les administrateurs peuvent bypasser le verrou si tu as une vraie raison de changer (faute de frappe, incident).</p>
"""

_QUOTA_OLD = """
<p>Pour préserver la file de téléchargement et éviter les abus, chaque utilisateur dispose d'un <strong>quota de demandes actives</strong>.</p>
<p>Une demande consomme une place de quota tant qu'elle est <em>en attente</em>, <em>validée</em> ou <em>en cours</em>. Dès qu'elle passe en <em>disponible</em>, <em>refusée</em> ou <em>indisponible</em>, la place se libère automatiquement.</p>
<ul>
  <li><strong>Quota standard</strong> : 5 demandes simultanées.</li>
  <li><strong>Quota augmenté</strong> : selon ton niveau et tes trophées, tu peux débloquer des places supplémentaires.</li>
  <li><strong>Demandes refusées récentes</strong> : si tu cumules trop de refus en peu de temps, le système peut temporairement réduire ton quota — il revient à la normale après quelques jours.</li>
</ul>
<p>Tu peux toujours voir ton quota courant en haut de l'onglet <strong>Demandes</strong>.</p>
"""

_QUOTA_NEW = """
<p>Le nombre de demandes que tu peux envoyer est limité <strong>par mois</strong>. C'est l'administrateur qui fixe cette limite, pour chaque membre.</p>
<ul>
  <li><strong>Chaque demande envoyée compte</strong>, quelle que soit la suite : approuvée, disponible ou refusée, elle reste comptée jusqu'à la fin du mois. Une demande renvoyée après un refus compte aussi.</li>
  <li>Une série compte pour <strong>une seule demande</strong>, même si tu coches plusieurs saisons.</li>
  <li>Le compteur repart à zéro <strong>le 1er de chaque mois</strong>.</li>
</ul>
<p><strong>Pour suivre ton compteur :</strong></p>
<ul>
  <li>Dans la fenêtre <strong>« Quoi de neuf aujourd'hui ? »</strong> (menu de ton avatar), case <strong>« Demandes restantes »</strong>.</li>
  <li>Après chaque demande, un message t'indique combien tu en as utilisé ce mois-ci.</li>
  <li>Tes demandes et leur état sont dans <strong>« Mes demandes »</strong>, sur <strong>« Mon profil »</strong>.</li>
</ul>
<p>Quand la limite est atteinte, le portail affiche <em>« Vous avez atteint votre quota de demandes pour ce mois. »</em> Attends le mois suivant, ou parles-en à l'administrateur.</p>
<p>L'administrateur peut aussi te laisser des demandes <strong>illimitées</strong>, ou choisir un quota <strong>automatique</strong> : il monte peu à peu quand tu es actif (visionnages, connexions, demandes, listes, tickets) et ne baisse qu'après une longue absence.</p>
"""

_XP_OLD = """
<p>L'<strong>XP</strong> (points d'expérience) fait monter ton niveau et débloque des paliers de grade : <em>Bronze → Argent → Or → Platine → Diamant → Maître → Légendaire</em>.</p>
<p>Voici les principales façons d'en gagner au quotidien :</p>
<ul>
  <li><strong>+10 XP</strong> par session de visionnage Emby (au moins 5 minutes regardées).</li>
  <li><strong>+25 XP</strong> quand tu termines un film.</li>
  <li><strong>+15 XP</strong> par épisode terminé.</li>
  <li><strong>+50 XP</strong> à la fin d'une saison complète.</li>
  <li><strong>+5 XP</strong> en notant un contenu après l'avoir vu.</li>
  <li><strong>+10 XP</strong> en publiant un commentaire constructif.</li>
  <li><strong>+20 XP</strong> en créant ou contribuant à une liste publique.</li>
  <li><strong>+15 XP</strong> en participant à une <em>watch party</em> ou à un événement saisonnier.</li>
  <li><strong>Multiplicateurs ponctuels</strong> : pendant un événement (XP boost), tous les gains sont multipliés (×2, ×3…).</li>
</ul>
<p><strong>Et les trophées ?</strong> Chaque trophée donne aussi de l'XP, mais le montant dépend de sa rareté. Pour connaître l'XP de chaque trophée, va voir l'onglet <strong>Trophées</strong> dans ton profil — chaque carte affiche son gain.</p>
"""

_XP_NEW = """
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

_RANKING_OLD = """
<p>Le <strong>classement</strong> que tu vois dans ta carte de profil est calculé sur les <strong>30 derniers jours glissants</strong>. Il met en avant les utilisateurs les plus actifs <em>récemment</em>, pas ceux qui cumulent depuis le début.</p>
<ul>
  <li>Ton <strong>rang</strong> (#1, #2…) reflète ta position parmi les utilisateurs publics.</li>
  <li>Le <strong>percentile</strong> indique dans quel pourcentage du haut tu te trouves (top 1 %, top 10 %…).</li>
  <li>La <strong>flèche de mouvement</strong> compare ton rang d'aujourd'hui à celui d'hier : ↗ tu progresses, ↘ tu recules.</li>
</ul>
<p>Le classement <strong>ignore les comptes administrateurs</strong> et les profils privés. Si tu masques ton profil, tu n'apparais plus dans la liste publique mais ton XP continue d'être comptabilisée.</p>
<p>Astuce : un mois de calme te fait redescendre. Pour rester en haut, regarde, note, commente régulièrement.</p>
"""

_RANKING_NEW = """
<p>Le <strong>classement</strong> compare l'activité des membres. Sur <strong>« Mon profil »</strong>, le bloc <strong>« Classement ce mois »</strong> montre ta place, et la carte <strong>« Classement »</strong> les premiers du moment. Touche le titre de la carte pour voir le classement complet.</p>
<p><strong>Quatre périodes :</strong> <em>Aujourd'hui</em>, <em>Semaine</em>, <em>Mois</em> et <em>Tout temps</em>. La semaine commence le lundi et le mois le 1er : à chaque nouvelle période, tout le monde repart de zéro.</p>
<p><strong>Ce qui compte :</strong> seulement l'XP gagnée par ton activité sur la période, c'est-à-dire les films et épisodes regardés, les connexions et les demandes. L'XP des trophées fait monter ton niveau, pas ton classement.</p>
<ul>
  <li>Ta <strong>place</strong> (#1, #2…) et ton <strong>« Top x% »</strong> te situent parmi les membres classés ce mois-ci.</li>
  <li>Dans ce bloc, l'écart (par exemple « +2 places ») compare ta place à celle de la fin du mois dernier. Dans la carte et le classement complet, la petite flèche compare avec la veille, la semaine dernière ou le mois dernier, selon la période choisie.</li>
  <li>Tant que tu n'as rien gagné sur la période, tu n'apparais pas.</li>
</ul>
<p><strong>Qui y figure :</strong> les membres au profil <em>public</em>. Si tu passes ton profil en <em>Privé</em> (<strong>Paramètres → Visibilité</strong>), tu disparais du classement, mais tu continues à gagner de l'XP.</p>
<p>Finir un mois dans le top 10, le top 5, le top 3 ou à la première place débloque les trophées <strong>« Compétiteur »</strong>.</p>
"""

_EVENTS_OLD = """
<p>Le bouton <strong>Calendrier</strong> dans la barre du haut ouvre le panneau des <strong>événements</strong> — soirées de visionnage, marathons saisonniers, watch parties.</p>
<p><strong>Ce que tu peux y faire :</strong></p>
<ul>
  <li><strong>Voir</strong> les événements à venir auxquels tu es invité.</li>
  <li><strong>Rejoindre</strong> un événement public en un clic.</li>
  <li><strong>Créer</strong> ton propre événement : choisis un titre, une date/heure, le contenu (film ou série), invite des participants, ajoute une description.</li>
  <li><strong>Discuter</strong> dans le chat dédié à chaque événement (avant, pendant et après le visionnage).</li>
</ul>
<p><strong>Bonus XP :</strong> participer à un événement te donne <strong>+15 XP</strong>, et certains trophées récompensent l'organisation ou la participation à plusieurs événements dans le mois.</p>
<p>Tu peux annuler un événement que tu as créé tant qu'il n'a pas commencé. Une notification est alors envoyée à tous les participants.</p>
"""

_EVENTS_NEW = """
<p>Les <strong>événements</strong> sont des séances de visionnage entre membres : un film, une série ou plusieurs titres à la suite (un marathon), à une date et une heure fixées.</p>
<p><strong>Trouver le calendrier :</strong> touche l'icône de calendrier dans la barre du haut. Sur téléphone, ouvre le menu de ton avatar puis <strong>« Calendrier »</strong>. La liste <strong>« Prochains événements »</strong> montre ceux où tu es invité, ceux que tu as créés et tous les événements publics.</p>
<p><strong>Répondre :</strong> touche un événement pour l'ouvrir, puis <strong>« Accepter »</strong> ou <strong>« Refuser »</strong>. Une fois inscrit, tu peux <strong>« Se désinscrire »</strong>. Un événement public plein affiche <em>« Complet »</em>.</p>
<p><strong>Créer un événement :</strong></p>
<ol>
  <li>Touche le bouton rond <strong>« + »</strong> en bas à droite, puis l'icône <strong>« Créer un événement »</strong>.</li>
  <li>Choisis <strong>Privé</strong> (sur invitation) ou <strong>Public</strong> (ouvert à tous).</li>
  <li>Donne un <strong>titre</strong>, cherche un ou plusieurs <strong>films ou séries</strong> déjà disponibles, puis choisis la <strong>date</strong> et l'<strong>heure</strong>.</li>
  <li>Pour un événement privé, ajoute tes <strong>invités</strong> : seuls les membres au profil public peuvent l'être. Pour un événement public, choisis le <strong>nombre de places</strong>. Tu peux ajouter un <strong>commentaire</strong>.</li>
  <li>Touche <strong>« Créer »</strong>.</li>
</ol>
<p><strong>Le moment venu :</strong> 15 minutes avant le début, le bouton <strong>« Entrer dans la salle »</strong> apparaît pour les inscrits. La salle s'ouvre dans un nouvel onglet : tu y retrouves les autres participants, le bouton pour lancer le film et le <strong>« Chat de la salle »</strong>.</p>
<p><strong>Annuler :</strong> si tu as créé l'événement, ouvre-le et touche <strong>« Annuler l'événement »</strong>.</p>
<p><strong>Notifications</strong> (la cloche) : tu es prévenu quand on t'invite, quand un invité répond à ton événement, quand un événement auquel tu es inscrit est annulé, ou si l'organisateur te retire. Un événement public est annoncé à tous les membres.</p>
<p>Participer ne rapporte pas d'XP en plus (le film regardé compte comme d'habitude). Créer des événements fait avancer les trophées <strong>« Organisateur »</strong>.</p>
"""

# slug -> (original starter text, its rewrite)
REWRITES = {
    "comment-faire-une-demande": (_REQUEST_OLD, _REQUEST_NEW),
    "choisir-son-pseudo": (_NAME_OLD, _NAME_NEW),
    "les-quotas-de-demandes": (_QUOTA_OLD, _QUOTA_NEW),
    "comment-gagner-de-l-xp": (_XP_OLD, _XP_NEW),
    "le-classement-mensuel": (_RANKING_OLD, _RANKING_NEW),
    "le-calendrier-et-les-evenements": (_EVENTS_OLD, _EVENTS_NEW),
}
TITLES = {
    "comment-faire-une-demande": "Comment faire une demande ?",
    "choisir-son-pseudo": "Choisir son pseudo",
    "les-quotas-de-demandes": "Les quotas de demandes",
    "comment-gagner-de-l-xp": "Comment gagner de l'XP ?",
    "le-classement-mensuel": "Le classement mensuel",
    "le-calendrier-et-les-evenements": "Le calendrier et la création d'événements",
}


def shape(body: str | None) -> str:
    """Tags, links and words of a body, its spacing and entity spelling aside."""
    spaced = html.unescape(body or "").replace("<", " <").replace(">", "> ")
    return " ".join(spaced.split())


def upgrade() -> None:
    bind = op.get_bind()
    # Found by its starter title, not its slug: an older editor save could move a
    # starter article's slug without touching a word of it.
    by_title = {title: slug for slug, title in TITLES.items()}
    rows = bind.execute(
        sa.text(
            "SELECT t.id, t.title, t.body_html FROM help_article_translations t "
            "JOIN help_articles a ON a.id = t.article_id "
            "WHERE t.lang = 'fr' AND a.deleted_at IS NULL AND t.title IN :titles"
        ).bindparams(sa.bindparam("titles", expanding=True)),
        {"titles": list(by_title)},
    ).fetchall()
    if not rows:
        return

    from services.portal.help_sanitize import sanitize_html

    untouched = [
        (row_id, by_title[title]) for row_id, title, body in rows
        if shape(body) == shape(sanitize_html(REWRITES[by_title[title]][0].strip()))
    ]
    for row_id, slug in untouched:
        bind.execute(
            sa.text(
                "UPDATE help_article_translations "
                "SET body_html = :body, updated_at = CURRENT_TIMESTAMP WHERE id = :id"
            ),
            {"body": sanitize_html(REWRITES[slug][1].strip()), "id": row_id},
        )


def downgrade() -> None:
    # Irreversible on purpose: the new text is right for the older code too.
    pass
