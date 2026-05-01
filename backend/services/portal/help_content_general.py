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
""".strip(),
        },
    },
]
