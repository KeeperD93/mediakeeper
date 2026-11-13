"""Help Center seed — Mon profil / Profile category (XP, paliers,
classement, recommandations, pseudo, avatar, visibilité, paramètres)."""
from __future__ import annotations

HELP_PROFILE: list[dict] = [
    {
        "slug": "comment-gagner-de-l-xp",
        "category": "profile",
        "icon": "Sparkles",
        "sort_order": 10,
        "fr": {
            "title": "Comment gagner de l'XP ?",
            "body_html": """
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
""".strip(),
        },
    },
    {
        "slug": "les-paliers-et-grades",
        "category": "profile",
        "icon": "Trophy",
        "sort_order": 20,
        "fr": {
            "title": "Les paliers et les grades",
            "body_html": """
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
""".strip(),
        },
    },
    {
        "slug": "le-classement-mensuel",
        "category": "profile",
        "icon": "Medal",
        "sort_order": 30,
        "fr": {
            "title": "Le classement mensuel",
            "body_html": """
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
""".strip(),
        },
    },
    {
        "slug": "comment-fonctionnent-les-recommandations",
        "category": "profile",
        "icon": "Wand2",
        "sort_order": 40,
        "fr": {
            "title": "Comment fonctionnent les recommandations ?",
            "body_html": """
<p>L'onglet <strong>Mon profil</strong> contient plusieurs sections de recommandations personnalisées. Chacune utilise un signal différent :</p>
<ul>
  <li><strong>Continuer à regarder</strong> — reprises de tes derniers contenus Emby commencés mais non terminés.</li>
  <li><strong>Pour toi</strong> — basé sur tes <em>genres préférés</em> (que tu peux modifier dans <em>Paramètres → Préférences</em>) et sur ta note moyenne par genre.</li>
  <li><strong>Parce que tu as aimé X</strong> — partage de TMDB des contenus similaires à ce que tu as récemment bien noté (≥ 8/10).</li>
  <li><strong>Tendances communauté</strong> — ce que les autres utilisateurs MediaKeeper regardent en ce moment, filtré pour ne pas te re-proposer ce que tu as déjà vu.</li>
  <li><strong>À ne pas manquer</strong> — sorties récentes (cinéma + streaming) qui correspondent à tes goûts.</li>
</ul>
<p>Plus tu <strong>notes</strong> et <strong>regardes</strong>, plus les recommandations s'affinent. Si une suggestion te paraît hors-sujet, baisse la note du contenu concerné — l'algorithme apprend de tes corrections.</p>
""".strip(),
        },
    },
    {
        "slug": "choisir-son-pseudo",
        "category": "profile",
        "icon": "AtSign",
        "sort_order": 50,
        "fr": {
            "title": "Choisir son pseudo",
            "body_html": """
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
""".strip(),
        },
    },
    {
        "slug": "ajouter-un-avatar-perso",
        "category": "profile",
        "icon": "ImagePlus",
        "sort_order": 60,
        "fr": {
            "title": "Ajouter un avatar personnalisé",
            "body_html": """
<p>Par défaut, ton avatar est récupéré depuis Emby. Tu peux le <strong>remplacer</strong> par une image de ton choix depuis <strong>Paramètres → Identité → Avatar</strong>.</p>
<ul>
  <li><strong>Formats acceptés</strong> : JPEG, PNG, WebP, GIF.</li>
  <li><strong>Taille maximale</strong> : 5 Mo.</li>
  <li><strong>Recommandation</strong> : image carrée, au moins 256×256 pixels, pour un rendu net dans toutes les vues (carte de profil, classement, commentaires).</li>
</ul>
<p>L'avatar personnalisé <strong>prend toujours le dessus</strong> sur l'avatar Emby. Pour revenir à l'avatar Emby, supprime simplement ton avatar personnalisé via le bouton dédié.</p>
<p>Ton avatar est stocké côté serveur et n'est jamais partagé avec un tiers.</p>
""".strip(),
        },
    },
    {
        "slug": "visibilite-du-profil",
        "category": "profile",
        "icon": "Eye",
        "sort_order": 70,
        "fr": {
            "title": "Visibilité du profil",
            "body_html": """
<p>Tu choisis dans <strong>Paramètres → Visibilité</strong> qui peut voir ton profil et tes statistiques :</p>
<ul>
  <li><strong>Public</strong> — n'importe quel utilisateur connecté peut consulter ta page <code>/portal/u/&lt;ton id&gt;</code>, voir ton niveau, tes trophées et tes genres préférés. Tu apparais dans le classement.</li>
  <li><strong>Privé</strong> — seul toi peux voir ta page. Les autres utilisateurs voient un écran <em>« Profil privé »</em>. Tu n'apparais plus dans le classement public.</li>
</ul>
<p>Tu peux aussi affiner finement :</p>
<ul>
  <li><strong>Masquer mes notes</strong> — tes scores ne sont pas affichés sur ta page publique.</li>
  <li><strong>Masquer mes listes</strong> — seules les listes que tu marques publiques restent visibles.</li>
  <li><strong>Masquer mes statistiques de visionnage</strong> — temps total, top genres, films/séries vus.</li>
</ul>
<p>Tu peux changer ces réglages à tout moment, sans cooldown.</p>
""".strip(),
        },
    },
    {
        "slug": "parametrer-son-compte",
        "category": "profile",
        "icon": "Settings",
        "sort_order": 80,
        "fr": {
            "title": "Paramétrer son compte",
            "body_html": """
<p>La page <strong>Paramètres</strong> regroupe tous les réglages de ton compte, organisée en 5 onglets :</p>
<ol>
  <li><strong>Identité</strong> — pseudo, bio, avatar.</li>
  <li><strong>Apparence</strong> — thème (clair / sombre / auto), accents personnalisés, animations.</li>
  <li><strong>Préférences</strong> — langue, genres préférés, contenu adulte (autorisé ou non), notifications par défaut.</li>
  <li><strong>Visibilité</strong> — qui peut voir ton profil, tes notes, tes listes (voir l'article dédié).</li>
  <li><strong>Compte</strong> — déconnexion globale, suppression des données, export.</li>
</ol>
<p>Toutes les modifications sont <strong>sauvegardées d'un seul coup</strong> via le bouton <em>Enregistrer</em> en bas de page. Tant que tu n'as pas cliqué, tes changements sont en attente — un bandeau pulse pour te le rappeler.</p>
""".strip(),
        },
    },
]
