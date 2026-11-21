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
<p>MediaKeeper te permet de demander un film ou une série qui n'est pas encore dans la bibliothèque. Tout se fait depuis la page d'accueil ou la recherche :</p>
<ol>
  <li>Sur la <strong>page d'accueil</strong>, un titre mis en avant se demande directement avec le bouton <strong>« Demander »</strong>.</li>
  <li>Sinon, tape son nom dans <strong>« Rechercher »</strong>, en haut (la loupe sur téléphone), puis choisis une suggestion ou parcours les résultats.</li>
  <li>Ouvre la fiche du titre et touche <strong>« Demander »</strong>. À la souris, le bouton apparaît aussi sur l'affiche, dans les résultats.</li>
  <li>Dans la fenêtre <strong>« Faire une demande »</strong>, valide. Pour une série, coche d'abord les saisons voulues.</li>
</ol>
<p>Le titre passe à <em>« Demandé »</em>. Une fois la demande approuvée et le titre ajouté, la cloche des notifications te prévient qu'il est disponible.</p>
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
""".strip(),
        },
    },
]
