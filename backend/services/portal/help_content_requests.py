"""Help Center seed — Portal / Requests category."""
from __future__ import annotations


HELP_REQUESTS: list[dict] = [
    {
        "slug": "comment-faire-une-demande",
        "category": "requests",
        "icon": "Send",
        "sort_order": 10,
        "fr": {
            "title": "Comment faire une demande ?",
            "body_html": """
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
""".strip(),
        },
    },
    {
        "slug": "les-differents-tags",
        "category": "requests",
        "icon": "Tags",
        "sort_order": 20,
        "fr": {
            "title": "Les différents tags",
            "body_html": """
<p>Chaque demande affiche un ou plusieurs <strong>tags colorés</strong> qui résument son état d'avancement en un coup d'œil :</p>
<ul>
  <li><strong>En attente</strong> — la demande vient d'être créée et attend la validation de l'administrateur.</li>
  <li><strong>Validée</strong> — l'administrateur a approuvé la demande, le téléchargement est planifié.</li>
  <li><strong>En cours</strong> — le contenu est en train d'être ajouté à la bibliothèque.</li>
  <li><strong>Disponible</strong> — c'est bon, le contenu est jouable sur Emby. Une notification t'a été envoyée.</li>
  <li><strong>Refusée</strong> — la demande n'a pas été retenue. La raison apparaît dans les commentaires.</li>
  <li><strong>Indisponible</strong> — le contenu n'est pas trouvable dans une qualité acceptable, ou bloqué pour des raisons techniques.</li>
  <li><strong>Doublon</strong> — un autre utilisateur a déjà demandé le même titre, vote sur la demande existante.</li>
</ul>
<p>Tu peux <strong>filtrer</strong> les demandes par tag depuis la liste, ce qui permet de voir rapidement « tout ce qui est dispo » ou « tout ce qui est en attente ».</p>
""".strip(),
        },
    },
    {
        "slug": "les-quotas-de-demandes",
        "category": "requests",
        "icon": "Gauge",
        "sort_order": 30,
        "fr": {
            "title": "Les quotas de demandes",
            "body_html": """
<p>Pour préserver la file de téléchargement et éviter les abus, chaque utilisateur dispose d'un <strong>quota de demandes actives</strong>.</p>
<p>Une demande consomme une place de quota tant qu'elle est <em>en attente</em>, <em>validée</em> ou <em>en cours</em>. Dès qu'elle passe en <em>disponible</em>, <em>refusée</em> ou <em>indisponible</em>, la place se libère automatiquement.</p>
<ul>
  <li><strong>Quota standard</strong> : 5 demandes simultanées.</li>
  <li><strong>Quota augmenté</strong> : selon ton niveau et tes trophées, tu peux débloquer des places supplémentaires.</li>
  <li><strong>Demandes refusées récentes</strong> : si tu cumules trop de refus en peu de temps, le système peut temporairement réduire ton quota — il revient à la normale après quelques jours.</li>
</ul>
<p>Tu peux toujours voir ton quota courant en haut de l'onglet <strong>Demandes</strong>.</p>
""".strip(),
        },
    },
]
