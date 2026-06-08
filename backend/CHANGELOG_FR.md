# Changelog

<!--
Section [Unreleased] : on accumule ici les petites modifications au fil du temps.
Quand on décide de publier, on remplace `[Unreleased]` par `[x.y.z] - YYYY-MM-DD`
et on met à jour APP_VERSION dans backend/api/changelog.py.
Cette section est volontairement sans date pour ne pas être affichée aux utilisateurs.
-->

## [Unreleased]

### Added
- Planificateur — scan d'index Emby (ajouts récents + complet), délai configurable.
- Portail — langue par défaut du portail configurable (réglages admin).
- Portail — réglage pour autoriser les demandes de contenu adulte (désactivé par défaut).
- Demandes — navigation par pages avec choix du nombre affiché (10/25/50/100).
- Problèmes (admin) — file de tickets paginée (10/25/50/100).
- Utilisateurs portail (admin) — liste paginée (10/25/50/100).
- Actualités (admin) — bouton « Charger plus » au-delà des 20 récentes.
- Utilisateurs portail (admin) — audit de la fiche : « Charger plus » au-delà de 100 entrées.
- Utilisateurs portail (admin) — fiche : « Charger plus » sur activité, trophées (XP) et sécurité.
- RGPD (admin) — suppressions en attente : bouton « Charger plus » au-delà de 50.
- Listes (admin) — modération : listes supprimées visibles/restaurables + « Charger plus ».
- Portail — lien de don configurable pour vos utilisateurs (réglages admin).
- Tableau de bord — cœur de soutien MediaKeeper dans le bandeau (Ko-fi, étoile).

### Changed
- Tableau de bord — 30 prochaines sorties affichées (au lieu de 20).

### Fixed
- Tableau de bord — onglets Historique (Notifications, Doublons) : bouton « Charger plus ».
- Tableau de bord — fil d'activité : mises à jour de plugin affichées dans votre langue.
- Tableau de bord — avatar et anneau de rang corrects dès la connexion (sans actualiser).
- Demandes (admin) — « Au nom de l'utilisateur » préréglé sur votre compte.
- Statistiques — médiathèques : nom Emby réel au lieu d'un sous-dossier (réparation auto).
- Problèmes (admin) — filtre par statut réparé (ne plante plus, n'est plus ignoré).
- Notifications — l'enregistrement d'un webhook Discord n'échoue plus.
- Notifications — le message test Discord suit la langue par défaut configurée.
- Stats — Utilisateurs et fusion : photo de profil (perso ou Emby) désormais affichée.
- Stats — survol des utilisateurs actifs : noms affichés au lieu des identifiants.
- Médiathèque — le détail des pistes n'échoue plus sur un fichier corrompu.
- Média Manager — annuler un renommage en lot ne s'interrompt plus à mi-chemin (réessai possible).
- Média Manager — libellés de l'historique de renommage suivent la langue de l'app.
- Média Manager — fenêtres accessibles : focus clavier, Échap, annonce lecteur d'écran.
- Média Manager — la tabulation clavier ignore les fenêtres et boutons masqués.
- Média Manager — fichiers alignés avec leurs noms générés à droite.
- Média Manager — fil d'ariane : repli du chemin trop long, séparateurs visibles.
- Média Manager — animations des fenêtres coupées si « réduire les animations » est actif.
- Tableau de bord — « Prochaines sorties » affichées dans votre langue.
- Tableau de bord — fil d'activité (connexions, lectures) affiché dans votre langue.
- Médiathèque — fiches détail TMDB affichées dans votre langue (repli anglais).
- Watchlist — séries, épisodes et synopsis affichés dans votre langue.
- Watchlist — films du calendrier affichés dans votre langue.
- Watchlist — mois et jours du calendrier suivent la langue de l'app.
- Watchlist — médias suivis (onglet Suivi) affichés dans votre langue.
- Notifications — toasts (module + lecture en cours) affichés dans votre langue.
- Notifications Discord — langue suit le défaut du portail.
- Liens TMDB — ouvrent la fiche dans la langue de l'app (watchlist, prochaines sorties).
- Dates affichées dans la langue de l'app (au lieu de celle du navigateur).
- Avatars personnalisés affichés dans la barre admin, la liste utilisateurs et les sessions.
- Portail — page Découvrir : bouton retour agrandi, survol collant et défilement latéral corrigés.

## [1.0.0-rc.4] - 2026-05-30

### Added
- Onboarding — module Portail ajouté au welcome et au tour.

### Changed
- Tableau de bord — cartes « Demandes » renommées « Portail Utilisateurs ».
- Interface admin — nouveau thème sombre, contraste texte renforcé pour la lisibilité.
- Avatars — anneau coloré par niveau (bronze → légendaire) sur toutes les surfaces, même rendu que le classement.
- Boutons — palette MediaKeeper appliquée (violet, rouge brique, vert forêt) sans toucher aux graphiques.
- Apparence — sélecteur d'accent retiré temporairement (palette MK verrouillée).
- Planificateur — interface réorganisée par catégories, cartes compactes.
- Démarrage — log boot : `COOKIE_SECURE=` renommé `COOKIE_HTTPS_FLAG=` (variable env inchangée).
- Cookie CSRF — validation par allowlist sur les polls (durcissement).
- Tableau de bord — titres des cartes uniformisés sur la nuance de texte atténuée.
- Menu latéral — cliquer un module ouvre son sous-menu sans quitter la page.

### Fixed
- Tableau de bord — carrousel des sorties scrollable à la main en animations réduites (était figé et tronqué).
- Admin — journal d'audit utilisateur : libellés d'action lisibles (certaines actions affichaient la clé brute).
- Admin — historique XP utilisateur : libellés d'action lisibles (octroi admin, surprise, trophée).
- Portail — bandeau événements : respecte les animations réduites (statique au lieu de défiler).
- Portail — pastille « Dispo » stable sur les ajouts Emby récents (plus de clignotement).
- Proxy d'images — les affiches ne renvoient plus de 429 quand une page en charge beaucoup d'un coup.
- Navigation portail — disponibilité et statut des demandes ne renvoient plus de 429 en défilement intense.
- Stats — sessions et actifs 24h : photo + anneau de niveau (parité classement).
- Stats — silhouette d'avatar correctement centrée dans l'anneau de niveau.
- Avatars Emby — photo rafraîchie sous 5 min après changement (au lieu de 7 jours).
- Connexion — la détection brute-force ignore désormais les variations de casse du nom d'utilisateur.
- Les schémas d'authentification rejettent désormais les clés JSON inconnues (défense en profondeur).
- Soirées ciné — accepter une invitation ne déclenche plus de faux avertissement de conflit horaire.
- Planificateur — les noms de tâches sont désormais traduits en français.
- Sécurité — codes d'erreur génériques et stables sur médiathèque, outils et TMDB.
- Sécurité — chemins médias validés et confinés à chaque point d'écriture (gestionnaire, analyses, fournisseurs).
- Sécurité — assainisseurs rendus linéaires (protection ReDoS).
- Proxy d'images et webhooks — durcis contre SSRF et DNS rebinding.
- Cookie CSRF — rotation aux frontières d'authentification (correction fixation de session).

## [1.0.0-rc.3] - 2026-05-22

### Fixed
- Connexion — l'assistant ne masque plus l'écran obligatoire de changement de mot de passe.
- Onboarding — l'étape Dossiers démarre vide (plus de noms anglais en dur).
- Onboarding — les dossiers médias sont optionnels (configurables après via Paramètres).

## [1.0.0-rc.2] - 2026-05-22

### Added
- Récupération mot de passe admin — outil CLI `scripts/reset_admin` + doc opérations.

### Changed
- Démarrage — l'avertissement cookies cite désormais l'option `COOKIE_SECURE=false` pour LAN HTTP.

### Fixed
- Crash de connexion sur installation neuve — migration `user_profiles.selected_title` manquante.
- Connexion — erreur lisible en cas d'échec de validation (plus de `[object Object]`).

## [1.0.0-rc.1] - 2026-05-21

### Added
- Admin Portail — bouton « Reset pseudo » (relance l'overlay de choix).
- Portal : nouveau composant jaquette « PosterCard » conforme i18n/tokens (préparation à l'intégration).
- Paramètres — nouvelle section Réseau avec cache d'images et cache DNS (toggles).
- Paramètres → Planificateur — section Cache (stats hits/manques + bouton Vider).
- Tableau de bord — réorganisation des cartes mobile via liste « Personnaliser ».
- Paramètres → Portail — bornes capacité événements (min/max par tranche de 5).

### Changed
- Doublons — barre d'actions épurée (Détections, Dernière détection)
- Santé — jaquettes 3 par ligne sur mobile, croix d'overlay repositionnée
- Santé — bouton « Remonter » masqué dans Configuration, icône bouton Analyser unifiée
- Demandes — admin : onglet « Paramètres » placé en premier (défaut à l'ouverture).
- Tableau de bord — agencement des cartes par défaut revu (8 widgets).
- Tableau de bord — carte « Lectures » retirée (info maintenue dans le bandeau).
- Tableau de bord — bandeau condensé sur mobile (3 stats + Services pleine ligne).
- Tableau de bord — compteurs lectures/alertes retirés du fil d'activité.
- Notifications — menu déroulant pleine largeur sur mobile.
- Santé — toggles refondus (commutateur slide accent ON, design pill harmonisé).
- Statistiques — pills filtres unifiées (style accent).
- Statistiques — tableaux Utilisateurs et Activité lisibles sur mobile (scroll horizontal).
- Suivi séries — barre d'outils refondue (recherche, filtres, export).
- Notifications — case « Activer » remplacée par toggle slide.
- Notifications — selects et inputs harmonisés (chevron custom).
- Onglets — interface compactée sur mobile.
- Pied de page — crédits TMDB compactés.
- Pied de page — bandeau d'attribution retiré (crédits conservés dans À propos).
- Avatar — sélecteur de couleur d'accent retiré (déplacé dans Paramètres → Apparence).
- Suivi — bouton « Restaurer » réaligné (radius unifié).
- Statistiques — records empilés en colonne sur mobile.
- Watchlist Manquants : nouveau label « Dernier scan », bouton renommé « Analyser ».
- Watchlist : bande TMDB allégée, jaquettes Suivi alignées sur le portail (mobile).
- Tableau de bord — avatars « En direct » alignés sur Utilisateurs (silhouette + tooltip).
- Tableau de bord — stats mobile compactées (icônes 34 px, libellés 3xs, valeurs lg).
- Tableau de bord — bouton « Personnaliser » déplacé dans le bandeau mobile.
- Barre du haut — sous-titre masqué sur mobile, titre centré dans le bandeau.
- Avatar barre du haut — aligné sur les fiches utilisateurs (photo + silhouette).

### Fixed
- Portal : limite débit /availability portée à 120/min, coalescing front, dédupe toasts 429
- Doublons — navigation entre onglets stabilisée (Ignorés → Historique/Règles)
- Doublons — premier accès accéléré, vue gardée en cache
- Doublons — bouton « Restaurer » réaligné sur les films (onglet Ignorés)
- Santé — sauvegarde de la configuration restaurée (toast de confirmation)
- Session admin expirée : reconnexion silencieuse sur Demandes, message clair ailleurs.
- Connexion — identifiant accepté quelle que soit la casse (majuscules/minuscules).
- Paramètres — libellés tâches Nettoyage demandes et Purge RGPD restaurés (planificateur).
- Portal — jaquettes mobile uniformisées sur les listes (3 colonnes, ratio 2/3).
- Tableau de bord — deep-link « Lecture Emby » hero corrigé (HTTPS + serverId).

## [0.9.9] - 2026-05-14

### Added
- Actualités admin — création, édition, suppression et planification (dates de début/fin)
- Mode maintenance Demandes personnalisable
- Demandes — auto-nettoyage configurable des demandes disponibles après N jours
- Demandes — total cumulé sous chaque compteur (attente, approuvées, refusées, disponibles)
- Demandes / Utilisateurs — refonte premium pleine largeur (recherche, filtres, table/cartes, actions groupées)
- Utilisateurs — drawer fiche 7 onglets (identité, accès, sécurité, activité, trophées, notes, audit)
- Utilisateurs — rôles et permissions granulaires (chat, demandes, problèmes, listes, XP hors-ligne)
- Utilisateurs — période d'accès (début/fin) avec prolongation rapide 1/3/6/12 mois
- Utilisateurs — désactivation du compte streaming depuis l'admin (sessions coupées)
- Utilisateurs — import sélectif via overlay et création manuelle de comptes locaux
- Utilisateurs — soft-delete réversible, journal d'audit, notes admin privées, tags
- Utilisateurs — export RGPD individuel (JSON) et notification ciblée admin → utilisateur
- Utilisateurs — indicateur en ligne, badge expiration < 7 j, filtre « jamais connectés »
- Utilisateurs — désactivation automatique à l'expiration (sessions coupées, audit dédié)
- Page À propos (stack, licences) et mentions partenaires sous Paramètres
- Page introuvable — vraie 404 accessible avec retour au tableau de bord
- Accessibilité — lien « Aller au contenu principal » au focus clavier
- Accessibilité — pièges au clavier sur 20 modales/overlays (Échap restaure le focus)
- Accessibilité — alternative clavier à la réorganisation des widgets du tableau de bord
- Accessibilité — toasts annoncés aux lecteurs d'écran (région aria-live)
- Accessibilité — animations décoratives respectent prefers-reduced-motion
- Gestionnaire — sélection au lasso dans les listes (Échap annule)
- Gestionnaire — marges cliquables élargies pour amorcer le lasso hors-ligne
- Gestionnaire — recherche TMDB : champ « Année » optionnel pour départager les remakes
- Suivi — pastilles de langues audio (FR, EN, JP…) sur les épisodes disponibles
- Sauvegardes — dump SQL et clé de chiffrement embarqués par défaut
- Sauvegardes — refus de démarrage si chemin absent en production
- Sauvegardes — guide opérateur de restauration et avertissement côté API
- Sauvegardes — vérification de signature ZIP et liste blanche d'entrées (anti zip-bomb)
- Runbook incidents avec procédures de récupération documentées
- Alertes webhook sur incidents critiques (santé, base, planificateur, dump)
- Confiance proxy stricte, en-têtes de sécurité (CSP/HSTS) et cookies sécurisés
- Sessions révocables, scopes de jetons stricts et WebSocket sécurisé
- Renforcement XSS — schémas d'URL filtrés, sanitisation HTML resserrée
- Renforcement API — limites de débit, contrôle d'origine, vérification d'autorisation
- CSP — endpoint dédié de remontée de violations avec journalisation rythmée
- API — paramètres de configuration : rejet des champs inconnus
- Notifications — signature HMAC sur les webhooks sortants
- Notifications — retry unique sur erreurs de débit (cap 5 s)
- Notifications — log structuré sur échec d'hébergement d'image (statut + extrait, pas de secret)
- Logs — filtre global de rédaction (mots de passe, jetons, JWT, webhooks)
- Connexion — succès journalisés avec identifiant utilisateur
- API — handler global d'erreur masque les paramètres de requête
- Confidentialité (RGPD) — section admin avec interrupteur, éditeurs FR/EN, comptes en attente
- Confidentialité (RGPD) — onglet utilisateur (politique, export ZIP, suppression différée, bandeau de grâce)
- Confidentialité (RGPD) — paramètres préchargés (désactivés par défaut), suppression différée annulable
- Utilisateurs — filtre « en attente de suppression »
- Planificateur — purge quotidienne des comptes en attente (opt-in)
- Base de données — chat anonymisé à la suppression d'un compte (au lieu d'être effacé)
- Démarrage — alerte si l'origine publique manque en mode reverse-proxy
- Bandeau persistant si la clé de chiffrement est éphémère
- Tests — détection automatique des domaines tiers absents de la politique de sécurité
- Déploiement — guides par stack reverse-proxy
- Documentation projet refondue (README, sécurité, architecture, contribution, attributions)
- UX — message clair quand le serveur limite les tentatives
- Paramètres notifications — confirmation obligatoire avant d'effacer toutes les destinations
- CSP — autorise le loader vidéo embarqué tout en conservant la lecture sans cookies

### Changed
- Demandes (admin) — en-tête épuré, interrupteurs glissants, éditeur de confidentialité mono-langue
- Portail admin — sous-onglets Tickets et Listes retirés (actions migrées vers la surface portail)
- Listes admin — modération depuis la page Listes du portail (onglet Admin)
- Dépendances frontend — alignement compile/runtime des locales

### Fixed
- Migrations — commit atomique de la séquence au démarrage (plus de rollback silencieux)
- Migrations — bascule en SQL natif sur les schémas concernés (corrige un no-op silencieux côté async)
- Migrations — colonne version élargie automatiquement pour les longues migrations
- Migrations — chaînage des têtes Alembic résolu
- Démarrage — validation trophées : fichiers locales inaccessibles n'invalident plus le seed
- Statistiques — popup jaquette se ferme après clic vers l'historique d'activité
- Modification utilisateur — vider un champ (prénom, nom, email) persiste comme suppression
- Modification utilisateur — formulaire reste à jour après sauvegarde
- Trophées — historique XP affiche le nom du trophée débloqué
- Trophées — Marathonien Ultime relevé à 24 h en une session (au lieu de 12 h)
- Notifications — détection contextuelle « série / saison complète / épisodes », template et synopsis appliqués
- Notifications — titres affichés en liens cliquables (au lieu de texte brut)
- Notifications admin — messages longs s'affichent sur plusieurs lignes
- Reconnexion — logo de l'overlay toujours affiché pendant un redéploiement, déconnexion auto si l'app a été mise à jour
- Tableau de bord — widget Activité : labels sur plusieurs lignes en fenêtre étroite
- Tableau de bord — boutons Reset/Terminé compacts en desktop, taille tactile préservée mobile
- Tableau de bord — widget Activité portail : chiffres centrés, plus de débordement
- Tableau de bord — barre Personnaliser : boutons à droite, Reset rouge, lecture sur une ligne
- Classement — flèche d'évolution séparée du pseudo (troncature propre sur les noms longs)
- Classement — avatar custom respecté dans toutes les listes, fallback initiale si l'image ne charge pas
- Portail — jaquettes plus compactes en mobile, tap ouvre la fiche (boutons retirés sur tactile)
- Portail — pastille de disponibilité unifiée (cache canonique prioritaire)
- Portail — bouton Lecture retiré des bannières héros (héros redevient informatif)
- Portail — vidéo héros collée sous la barre du haut à toutes les largeurs
- Portail — corrige une erreur 500 quand un identifiant TMDB est envoyé en texte
- Planificateur — bouton « Lancer maintenant » sur tâches obsolètes ne renvoie plus d'erreur
- Suivi / Manquants — séries dupliquées affichées une seule fois
- Suppression d'utilisateur — contenus communautaires anonymisés au lieu d'être effacés
- PWA — URLs portail alignées, nom système unifié, icône maskable corrigée
- PWA — icônes Android opaques sur toutes les variantes
- Confidentialité — onglet anglais affichait la clé brute (traduction restaurée)
- Confidentialité — message d'erreur propre quand l'export dépasse la limite
- Base de données — contraintes manquantes ajoutées sur les tables d'événements et d'XP
- Connexion — icône GitHub restaurée avec le bon lien, ligne version texte retirée
- Build — fin de ligne LF forcée sur scripts, auto-fix CRLF au build conteneur
- UX — padding crédits resserré, lien GitHub login dédupliqué, mention conteneur retirée
- Utilisateurs — compte admin local marqué « Local » au lieu d'une source externe
- Utilisateurs — date de dernière connexion admin renseignée à chaque login
- Utilisateurs — bandeau de stats actualisé immédiatement après désactivation
- Utilisateurs — drawer ne se ferme plus au clic en dehors (croix uniquement)
- Utilisateurs — fin d'accès affichée en heures/minutes quand il reste moins de 24 h
- Utilisateurs — colonne Statut en vert/rouge selon l'état du compte
- Utilisateurs — date de début d'accès pré-remplie avec la création du compte
- Utilisateurs — onglet Audit traduit et résumé en clair
- Utilisateurs — onglet Trophées : noms traduits, icônes alignées sans animation, badge rareté + XP
- Utilisateurs — picto calendrier visible sur les champs date
- Utilisateurs — bouton « Forcer la déconnexion » précise qu'il ne touche pas le compte streaming
- XP — comptes inactifs cumulent désormais l'XP si l'admin coche « XP hors-ligne »
- XP — attribution post-session ne crashe plus en cas de session ORM expirée
- XP — durée de visionnage clampée au runtime (longue pause ne dépasse plus 85 % artificiellement)
- XP — bandes-annonces et types non Movie/Episode ne donnent plus d'XP
- XP — table d'actions nettoyée des entrées fantômes (couvertes par les trophées)
- Sessions — durée réelle utilisée (clamp), plus de fausses sessions de 24 h+ après redémarrage
- Sessions — fin marquée à la dernière apparition (au lieu du moment de détection)
- Debug admin — bouton « Re-vérifier tous les trophées » pour rattraper l'historique
- Debug admin — bouton « Réinitialiser un trophée pour tous » (suppression + remboursement XP)
- Profil — classement du mois affiche les 15 lignes sans scroll interne
- Doublons — onglet Ignorés en lignes compactes groupées par série, bouton « Tout restaurer »
- Sécurité — suppression d'`unsafe-eval` dans la CSP (locales précompilées)
- Statistiques — Top 20 et stats par genre comptent selon les mêmes règles

## [0.9.8] - 2026-04-28

### Removed
- Thèmes alternatifs retirés — seul le thème sombre reste, retour à la v1.0

### Added
- Tickets — refonte complète : ancrage à un titre (saison/épisode pour les séries) ou hors médias, conversation premium, filtres statut/source/type
- Tickets — alerte admin à l'ouverture, fermeture auto après 7 j sans activité
- Gestionnaire — déplacement : suggestion d'un dossier homonyme du parent en tête de liste (badges « Suggéré » / « ~Suggéré »)
- Gestionnaire — déplacement : carte « Créer un dossier ici » avec saisie inline (Entrée crée + sélectionne)
- Gestionnaire — bouton « copier » sur chaque nouveau nom généré
- Tableau de bord — nouvelle carte « Demandes — événements à venir » (5 prochains événements du portail)
- Tableau de bord mobile — pile verticale automatique sur smartphone
- Tableau de bord — deux cartes Demandes (actions / activité, bascule 24h/7j)
- Onglet « Listes » dans l'admin Demandes (modération des listes publiques)
- Page de gestion des demandes (admin) : backdrops, stats hebdo, filtres, tri, actions rapides
- Backdrop ajouté aux demandes (TMDB à la création, backfill auto)
- Changement de mot de passe admin dans Paramètres → Général
- Onglet Sécurité (Paramètres) : historique connexions, blocage IP/utilisateur
- Blocage auto après 5 tentatives ratées, alerte après 3
- Clés sensibles (Emby, TMDB, OpenSubtitles…) chiffrées en base
- Barre de navigation mobile style app (bottom bar + encoche iPhone)
- Expérience mobile peaufinée (touch targets, hover désactivé sur tactile)
- Administration mobile : touch targets élargis, drawer + encoche, tableaux en mode carte
- Gestionnaire — onglet « Mots à ignorer » : liste éditable des tags retirés avant recherche TMDB

### Changed
- Sidebar — section « Demandes » renommée « Module Demandes »
- Sidebar — sous-onglets exposés directement sous chaque module (plus de barres internes), auto-expand
- Configuration Module Demandes accessible depuis la sidebar (sous Utilisateurs)
- Demandes — listes scrollables : flèches latérales sur desktop, swipe natif sur tactile
- Gestionnaire — overlay de déplacement refondu (modale 960×640, breadcrumb, suggestion auto, recents en accordéon)
- Gestionnaire — overlay « Organiser les dossiers » refondu (mêmes codes que la modale de déplacement)
- Gestionnaire — overlay « Renommer le dossier » refondu (mêmes codes)
- Sidebar — catégorie « Médias » renommée « Modules »
- Filtres harmonisés sur tous les modules (style pill, halo accent sur l'actif)
- Paramètres → Apparence : curseur « Intensité des néons » (0 % à 200 %)
- Page de connexion : auto-fill du navigateur désactivé
- URLs d'administration standardisées (anciens bookmarks à refaire)
- Notifications : ouvrir la cloche marque tout comme lu (bouton « Tout marquer » retiré)
- Sidebar — pastille chiffrée des notifications retirée
- Sous-titres — Bibliothèque : filtres redécoupés en 3 groupes
- Sous-titres — quota OpenSubtitles remonté en haut, visible depuis tous les onglets
- Erreurs backend traduites côté interface (plus d'anglais brut)
- Suppression d'une demande par l'admin : ligne complètement retirée (resoumission immédiate)
- Pastille de reprise (x2, x3…) passée au rouge pour s'aligner sur « Rejeté »
- Fiche utilisateur (Statistiques) : layout compacté, nom complet au survol
- Notifications Discord : épisodes regroupés par saison dès 2 ajouts

### Fixed
- Notifications Discord — ajouts récents : fiche rafraîchie depuis Emby à l'envoi (différée si résumé/année manquants)
- Gestionnaire — assainissement : « / » et « \ » remplacés par un espace (plus de mots collés)
- Gestionnaire — déplacement : recherche réinitialisée en changeant de dossier ou catégorie
- Gestionnaire — déplacement : structure HTML des cartes corrigée (boutons imbriqués)
- Gestionnaire — recherche TMDB : breadcrumb relance la recherche sur le parent
- Gestionnaire — recherche TMDB : sélection multiple gérée si tous partagent le même titre nettoyé
- Gestionnaire — renommage : liste resynchro auto avec le NAS (plus d'erreur « source not found »)
- Gestionnaire — modale de conflit / erreurs de renommage : libellés localisés
- Gestionnaire — renommage : titres terminant par « … » ou « ... » plus rejetés
- Gestionnaire — lasso : sélection correcte après scroll
- Gestionnaire — Ajouter saison : épisodes liés aux fichiers cochés, extension préservée
- Gestionnaire — fichier renommé reste à sa place dans la liste
- Tableau de bord — Activité récente : titres et libellés ne suivent plus la couleur d'accent
- Tableau de bord mobile — en-tête : titre plus tronqué par les points et avatars
- Suivi mobile — Timeline : titres plus tronqués (2 lignes si besoin)
- Suivi mobile — Calendrier : cases carrées avec numéro + pastille événements
- Suivi mobile — Ignorés : nom, tags et bouton « Restaurer » empilés verticalement
- Suivi — Ignorés : info-bulle au survol du nom de série tronqué
- Statistiques mobile — Utilisateurs & Activité : titre/filtres/recherche empilés
- Statistiques mobile — Fiche utilisateur : popup recadrée et scrollable, en-tête collant
- Statistiques mobile — Graphiques : boutons sur toute la largeur, plus tronqués
- Titres d'onglet du navigateur corrigés sur le module Demandes
- Tableau de bord — carte « Demandes — à traiter » plus tronquée avec bouton Gérer
- Disponibilité d'un titre récemment ajouté reflétée sous 1 minute (plus de reload)
- Classement du mois : plus d'erreur 401 si l'admin n'est pas connecté au viewer
- Statistiques : libellés et durées (Record, Streak, Top, Pic, « il y a … ») en français
- Gestionnaire : mot « Custom » ignoré dans la détection auto du titre TMDB
- Notifications Discord : jaquettes affichées, lien TMDB sur épisodes, textes par défaut FR
- Notifications Discord : délai correctement interprété en secondes (plus ×60)
- Sous-titres mobile — Rechercher : sélecteurs et boutons empilés
- Notifications mobile — Modèles : liste, éditeur, aperçu Discord empilés
- Onboarding mobile : barre d'étapes scrollable, panneaux adaptés, touch targets élargis
- Demandes — accueil mobile : titre « Top 20 du mois » plus grignoté par le hero
- Demandes — accueil mobile : hero raccourci (52 vh) pour remonter les carrousels
- Demandes — nav mobile : logo + icônes sur une seule ligne
- Demandes — top nav mobile : gradient sombre atténué pour laisser voir le hero
- Demandes — hero mobile : son du trailer activé en touchant le hero (bouton son retiré)
- Demandes — hero desktop : titre, synopsis et boutons rapprochés du bas
- Demandes — hero : voile noir de transition désormais plein écran
- Demandes — hero mobile : boutons d'action compactés pour tenir sur 400 px
- Demandes — hero mobile : trailer bord à bord (masque ellipse retiré)
- Demandes — top bar : calendrier et cloche alignés à 100 % sur le style des autres icônes

## [0.9.7] - 2026-04-17

### Added
- Carrousel « Basé sur vos préférences » piloté par un sélecteur de genres dans Modifier mon profil
- Cartes profil enrichies : plus long marathon, répartition films/séries, tranches horaires, mois record
- 11 genres supplémentaires mappés (Histoire, Western, Guerre, etc.)
- 4 trophées Mythiques et 7 méta-trophées « Maîtres » avec effets d'avatar uniques
- 6 niveaux de rareté pour les trophées, avec effets animés pour les plus rares
- Overlay trophées : recherche, filtre « Avec récompense » et épinglage de 5 succès sur le profil
- Sélecteur de titre équipé dans Modifier mon profil
- Navigateur de dossiers intégré à l'onboarding
- Quota mensuel de demandes affiché en toast, comptes admin illimités

### Changed
- Refonte du profil Demandes : nouvel ordre des sections et carrousels de recommandations
- Classement mensuel étendu au top 15 avec flèches de progression
- Dashboard : widget Top utilisateurs remplacé par le classement XP mensuel
- Cartes du Dashboard avec icônes colorées (lectures, durée, stockage, doublons)
- Trophées secrets aussi visibles dans leur catégorie naturelle
- Votes sur les demandes retirés : une œuvre demandée reste unique
- Actions sensibles du backoffice mieux protégées contre les doubles clics
- Tickets : raccourci dans le menu avatar et notification de réponse admin

### Fixed
- Filtrage strict des lectures sans jaquette ou sans correspondance TMDB
- Détection « Déjà vu » basée sur Emby au lieu de la table locale
- Regroupement des épisodes d'une même série dans « Continuer à regarder »
- Recommandations par genre avec opérateur OR pour plus de résultats
- Fenêtre « Faire une demande » redessinée avec prise en compte de la disponibilité partielle
- Compteur « Le plus revu » stabilisé contre les sessions corrompues
- URL publique Emby conservée à l'activation / désactivation de l'outil
- Tag « Demandé » affiché instantanément après envoi
- Noms d'épisodes : fallback anglais si TMDB renvoie un placeholder
- Sauvegarde effective des champs « masquer adulte » et « titre équipé »
- Épisodes ignorés par l'admin respectés dans la fenêtre de demande
- Bouton « Demander » de la fiche détaillée ouvre bien la fenêtre de demande

## [0.9.6] - 2026-04-14

### Added
- Système de trophées : 150+ succès répartis en ~20 familles + 29 trophées secrets à débloquer
- Système de niveaux (max 50) basé sur l'XP
- Badges d'années sur les trophées saisonniers (Noël, Halloween, Nouvel An…)
- Titres de récompense affichés dans la sidebar et le classement
- Overlay plein écran dédié aux trophées, avec catégories et détails par succès
- Statistiques profil enrichies : date d'inscription, rang, genres, jour favori, films et séries les plus revus

### Fixed
- Temps de visionnage total affiché à 0h
- Certains trophées secrets ne se débloquaient pas

## [0.9.5] - 2026-04-13

### Added
- Page profil Demandes refaite avec un nouveau design
- Système de rangs visuels à 7 paliers (Bronze → Légendaire) avec effets visuels progressifs
- Cartes de genres horizontales, mini graphique du jour favori, section « Le plus revu »
- Section trophées avec grille visuelle et progression vers le prochain succès
- Classement mensuel basé sur l'XP avec avatars colorés et titres des joueurs
- Bloc « Membre depuis X mois » dans la sidebar

### Changed
- Le classement utilise désormais l'XP gagné ce mois au lieu du nombre de lectures

## [0.9.4] - 2026-04-05

### Added
- Refonte complète du module Sous-titres avec gestionnaire intégré
- Navigateur de bibliothèque avec grille de jaquettes responsive (compatible 21:9)
- Overlay détaillé pour films et séries : sous-titres, pistes audio, recherche et téléchargement
- Regroupement automatique des épisodes par série
- Suppression de pistes audio et sous-titres directement depuis l'interface
- Recherche et téléchargement via OpenSubtitles avec scoring de qualité
- Profils de langues pour les sous-titres
- Historique des téléchargements persistant
- Vue matricielle saison × épisode pour les séries
- Téléchargement par lot avec suivi de progression
- Téléchargement automatique des sous-titres pour les nouveaux médias
- Mode audit complet (manquants, forcés, image, encodage)
- Détection et correction manuelle de la désynchronisation SRT
- Correction automatique de l'encodage des sous-titres
- Comparateur de sous-titres côté à côté
- Recherche de flux dans la bibliothèque avec suppression de masse
- Support étendu à 28 langues (arabe, chinois, coréen, japonais, hindi, etc.)

### Changed
- Internationalisation complète : tout le texte de l'interface est désormais traduit
- Les dates et heures s'affichent dans la locale du navigateur

### Fixed
- « Top langue audio » affiché à la place de « Langue audio » dans les lectures en cours
- Les sous-titres image (PGS) sont maintenant comptés dans les pills de langues
- L'overlay des films fonctionne à nouveau
- Le filtre « Manquant » est plus rapide
- L'onglet Statistiques ne charge plus en boucle

## [0.9.3] - 2026-04-02

### Added
- Catégories dynamiques dans le Media Manager avec navigateur de dossiers intégré
- Sélection lasso (rectangulaire) dans la liste de fichiers
- Menu contextuel (clic droit) sur les fichiers, dossiers et noms générés
- Navigation au clavier avec la touche Retour arrière pour remonter dans les dossiers
- Filtrage par extension de fichier dans le module Santé avec puces cliquables
- L'extraction de fichiers peut désormais être annulée depuis l'historique

### Changed
- La fenêtre de configuration du Media Manager est plus compacte
- Les onglets du Media Manager occupent toute la largeur avec défilement horizontal
- Le nettoyage automatique des noms de fichiers supprime aussi les balises `[...]`, `(...)` et `10BITS` / `8BITS`
- Les prochaines sorties du Dashboard affichent les épisodes jusqu'à 2 jours passés avec un badge dédié

### Fixed
- Les filtres du module Santé restaient masqués quand aucun résultat ne correspondait
- Le menu déroulant des règles de doublons était illisible en mode clair
- Les films et séries suivis n'apparaissaient pas dans le calendrier
- Décalage horaire de 2h corrigé
- Les tâches planifiées démarrent désormais à minuit pour les intervalles ≥ 1h

## [0.9.2] - 2026-03-31

### Added
- Suppression groupée des activités dans Statistiques / Activité

### Changed
- Le graphique radar « Top par genre » est plus grand pour une meilleure lisibilité
- Les boutons d'export CSV / JSON dans Watchlist / Manquants sont plus grands et plus visibles

### Fixed
- La carte « Doublons » du Dashboard affichait un mauvais compte en incluant les doublons ignorés
- La popup profil utilisateur dans Statistiques s'ouvrait sous la sidebar
- Les exclusions de contenu n'étaient pas appliquées aux statistiques utilisateurs
- Le menu déroulant des exclusions était illisible en mode clair
- Les films et séries suivis n'apparaissaient pas dans le calendrier Watchlist

## [0.9.1] - 2026-03-29

### Added
- Nouveau système de changelog avec popup « Quoi de neuf ? » et page dédiée accessible depuis la sidebar
- Notifications Discord disponibles en français et en anglais, avec adaptation automatique à la langue choisie
- Nouveau module Santé médias avec widget Dashboard (score global, codecs obsolètes, résolution, sous-titres manquants)
- Nouveau module Sous-titres : recherche et téléchargement via OpenSubtitles
- Nombre de jours personnalisé dans les graphiques de statistiques

### Changed
- Les dates et heures s'affichent dans le fuseau horaire de votre navigateur
- Les pages Statistiques et Notifications sont entièrement traduites
- Le numéro de version dans la sidebar est dynamique et cliquable
- Navigation dans les historiques plus fiable (plus de doublons ou d'éléments manquants)

### Fixed
- Les prochaines sorties s'affichent dès le lancement
- Le compteur de la Watchlist apparaît immédiatement au démarrage
- Les tests de notification Discord envoient le bon type de message
- Les jaquettes ne disparaissent plus après le premier test Discord
- L'aperçu des notifications n'affiche plus deux messages superposés
- Le graphique d'activité respecte le nombre de jours sélectionné

## [0.9.0] - 2026-03-15

### Added
- Sauvegarde et restauration complètes de la configuration
- Téléchargement, restauration ou suppression des sauvegardes depuis les Paramètres
- Sauvegarde automatique programmable dans le planificateur

### Changed
- Refonte de l'assistant de première configuration

## [0.8.0] - 2026-03-01

### Added
- Planificateur de tâches : gérez vos tâches automatiques depuis les Paramètres
- Assistant de première configuration pour guider les nouveaux utilisateurs

## [0.7.0] - 2026-02-15

### Added
- 11 thèmes visuels au choix (sombre, AMOLED, Nord, Sakura, Cinema, et plus)
- Personnalisation avancée : arrondis ajustables, fond d'écran avec opacité et flou
- Nouvelle interface des Paramètres organisée en onglets

## [0.6.0] - 2026-02-10

### Added
- Interface disponible en français et en anglais
- Sélecteur de langue dans la barre du haut
- Détection automatique de la langue du navigateur

## [0.5.0] - 2026-02-01

### Added
- Nouvelle interface complète : Dashboard, Statistiques, Doublons, Journaux, Watchlist, Notifications, Paramètres
- Carrousel des lectures en cours sur le Dashboard
- Bandeau de statistiques en temps réel
- 6 widgets personnalisables sur le Dashboard
