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
<p>Le <strong>classement</strong> que tu vois dans ta carte de profil est calculé sur les <strong>30 derniers jours glissants</strong>. Il met en avant les utilisateurs les plus actifs <em>récemment</em>, pas ceux qui cumulent depuis le début.</p>
<ul>
  <li>Ton <strong>rang</strong> (#1, #2…) reflète ta position parmi les utilisateurs publics.</li>
  <li>Le <strong>percentile</strong> indique dans quel pourcentage du haut tu te trouves (top 1 %, top 10 %…).</li>
  <li>La <strong>flèche de mouvement</strong> compare ton rang d'aujourd'hui à celui d'hier : ↗ tu progresses, ↘ tu recules.</li>
</ul>
<p>Le classement <strong>ignore les comptes administrateurs</strong> et les profils privés. Si tu masques ton profil, tu n'apparais plus dans la liste publique mais ton XP continue d'être comptabilisée.</p>
<p>Astuce : un mois de calme te fait redescendre. Pour rester en haut, regarde, note, commente régulièrement.</p>
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
<p>À ta première connexion sur le portail, MediaKeeper te demande de <strong>choisir un pseudo</strong>. Quelques règles à connaître :</p>
<ul>
  <li>Le pseudo doit être <strong>unique</strong> sur la plateforme (insensible à la casse : « Lola » et « lola » sont identiques).</li>
  <li>Longueur entre 2 et 50 caractères. Lettres, chiffres, espaces, tirets et apostrophes acceptés.</li>
  <li>Certains noms sont <strong>réservés</strong> et refusés : <em>admin, administrator, administrateur, root</em>.</li>
  <li>Si le pseudo est déjà pris, MediaKeeper te propose <strong>jusqu'à 5 suggestions</strong> libres (avec un suffixe numérique).</li>
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
