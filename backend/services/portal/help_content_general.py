"""Help Center seed — General + Issues + Misc categories.

Smaller buckets bundled here so each category file stays close in size to
the others (300-line file-size convention)."""
from __future__ import annotations


HELP_GENERAL: list[dict] = [
    {
        "slug": "les-notifications",
        "category": "general",
        "icon": "Bell",
        "sort_order": 10,
        "fr": {
            "title": "Les notifications — à quoi servent-elles ?",
            "body_html": """
<p>Les notifications te tiennent au courant de tout ce qui te concerne sur le portail, sans avoir à le rafraîchir.</p>
<p><strong>Ce qui te notifie :</strong></p>
<ul>
  <li>Une de tes demandes change de statut (validée, en cours, disponible, refusée).</li>
  <li>Le contenu que tu as demandé est <strong>maintenant disponible</strong> sur Emby.</li>
  <li>Quelqu'un te <strong>répond</strong> sur un ticket ou un commentaire.</li>
  <li>Tu débloques un <strong>trophée</strong>.</li>
  <li>Tu changes de <strong>palier de niveau</strong>.</li>
  <li>Tu es <strong>invité à un événement</strong> (watch party, événement saisonnier).</li>
  <li>Une de tes <strong>listes collaboratives</strong> est modifiée.</li>
</ul>
<p>Tu peux désactiver chaque catégorie individuellement dans <strong>Paramètres → Préférences → Notifications</strong>. Les notifications critiques (sécurité du compte) restent toujours actives.</p>
""".strip(),
        },
    },
    {
        "slug": "regarder-du-contenu-surprise",
        "category": "general",
        "icon": "Shuffle",
        "sort_order": 20,
        "fr": {
            "title": "Regarder du contenu surprise (bouton Surprise)",
            "body_html": """
<p>En bas à droite de l'écran, le <strong>bouton Surprise</strong> (icône de dés) te propose au hasard <strong>un film ou un épisode</strong> à regarder, sélectionné parmi les contenus :</p>
<ul>
  <li>Disponibles sur Emby.</li>
  <li>Que tu n'as <strong>pas encore vus</strong>.</li>
  <li>Compatibles avec tes <strong>genres préférés</strong>.</li>
  <li>Notés positivement par la communauté.</li>
</ul>
<p>Tu peux relancer la roulette autant de fois que tu veux ; chaque clic propose un nouveau titre. Si rien ne te tente, ferme simplement la fenêtre.</p>
<p>C'est l'outil parfait quand tu hésites devant la bibliothèque pendant 20 minutes sans rien lancer.</p>
""".strip(),
        },
    },
]


HELP_ISSUES: list[dict] = [
    {
        "slug": "comment-creer-un-ticket-de-probleme",
        "category": "issues",
        "icon": "LifeBuoy",
        "sort_order": 10,
        "fr": {
            "title": "Comment créer un ticket de problème ?",
            "body_html": """
<p>Si quelque chose ne fonctionne pas (lecture qui plante, sous-titres absents, demande bloquée, fonctionnalité étrange), tu peux ouvrir un <strong>ticket</strong> que les administrateurs traiteront.</p>
<ol>
  <li>Ouvre le menu avatar (en haut à droite) → <strong>Mes tickets</strong>.</li>
  <li>Clique sur <strong>« Nouveau ticket »</strong>.</li>
  <li>Choisis une <strong>catégorie</strong> : lecture, demande, compte, autre.</li>
  <li>Donne un <strong>titre court</strong> (ex. « Pas de son sur l'épisode 3 de XYZ »).</li>
  <li>Décris le problème avec un <strong>maximum de détails</strong> : quel appareil, quel navigateur ou app Emby, à quel moment, message d'erreur visible.</li>
  <li>Tu peux joindre une capture d'écran si elle aide.</li>
  <li>Valide. L'administrateur reçoit une notification immédiate.</li>
</ol>
<p>Tu peux suivre l'état de tes tickets et y ajouter des messages depuis <strong>Mes tickets</strong>. Une réponse de l'admin déclenche une notification.</p>
""".strip(),
        },
    },
]


HELP_MISC: list[dict] = [
    {
        "slug": "le-calendrier-et-les-evenements",
        "category": "misc",
        "icon": "CalendarDays",
        "sort_order": 10,
        "fr": {
            "title": "Le calendrier et la création d'événements",
            "body_html": """
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
""".strip(),
        },
    },
]
