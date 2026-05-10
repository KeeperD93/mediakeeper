# Changelog

<!--
Section [Unreleased] : on accumule ici les petites modifications au fil du temps.
Quand on décide de publier, on remplace `[Unreleased]` par `[x.y.z] - YYYY-MM-DD`
et on met à jour APP_VERSION dans backend/api/changelog.py.
Cette section est volontairement sans date pour ne pas être affichée aux utilisateurs.
-->

## [Unreleased]

### Added
- Accessibilité — lien « Aller au contenu principal » au focus clavier (connexion + admin)
- Page introuvable — vraie page 404 accessible avec retour au tableau de bord (plus de redirection silencieuse)
- UX page crédits resserrée et lien GitHub sur la page de connexion
- À propos — page admin (stack, licences, FFmpeg LGPL) et mentions sous TMDB / OpenSubtitles dans Paramètres
- Demandes — cartes statistiques affichent désormais le total cumulé sous chaque compteur (en attente, approuvées, refusées, disponibles)
- Demandes / Utilisateurs — refonte premium pleine largeur (recherche, filtres, vue tableau/cartes, actions groupées)
- Utilisateurs — drawer fiche utilisateur 7 onglets (identité, accès, sécurité, activité, trophées, notes, audit)
- Utilisateurs — refonte cartes Activité (icônes contextuelles, jauges colorées) et permissions en interrupteurs bleus
- Utilisateurs — rôles + permissions granulaires (chat, demandes, problèmes, listes, XP hors-ligne)
- Utilisateurs — période d'accès (début/fin) avec prolongation rapide 1/3/6/12 mois
- Utilisateurs — désactivation du compte streaming depuis MK (sessions actives coupées)
- Utilisateurs — import sélectif via overlay et création manuelle de comptes locaux
- Utilisateurs — soft-delete réversible, journal d'audit complet, notes admin privées, tags
- Utilisateurs — export RGPD individuel (JSON) et notification ciblée admin → utilisateur
- Utilisateurs — indicateur en ligne, badge expiration < 7 j, filtre « jamais connectés »
- Utilisateurs — désactivation automatique à l'expiration (Emby + MediaKeeper, sessions coupées, audit dédié)
- Documentation projet (README, SECURITY, ARCHITECTURE, CONTRIBUTING, attributions)
- Sauvegardes — dump SQL et clé de chiffrement embarqués par défaut
- Sauvegardes — refus de démarrage si BACKUP_PATH absent en production (sécurité)
- Sauvegardes — guide opérateur de restauration + avertissement explicite côté API
- Runbook incidents avec procédures de récupération documentées
- Alertes webhook automatiques sur incidents critiques (santé, base, planificateur, dump)
- Mises à jour sécurité (JWT, chiffrement, multipart, build frontend)
- Confiance proxy stricte, en-têtes sécurité (CSP/HSTS) et cookies sécurisés
- Sessions révocables, scopes tokens stricts et WebSocket sécurisé
- Renforcement XSS — schémas d'URL filtrés, sanitization HTML resserrée
- CSP — autorise le loader YouTube et conserve l'iframe sans cookies
- Renforcement API — limites de débit, contrôle d'origine, vérification d'autorisation
- CSP — endpoint dédié de remontée de violations + journalisation rythmée
- Déploiement — guides par stack reverse-proxy (LAN, DSM, NPM, Caddy, Traefik)
- UX — message clair quand le serveur limite les tentatives
- Paramètres notifications — confirmation explicite obligatoire avant d'effacer toutes les destinations
- Démarrage — alerte si l'origine publique manque en mode reverse-proxy
- Bandeau d'alerte persistant si la clé de chiffrement est éphémère
- Tests — détection automatique des domaines tiers absents de la politique de sécurité
- Sauvegardes — vérification de signature ZIP et liste blanche d'entrées (anti zip-bomb)
- API — paramètres de configuration : rejet des champs inconnus (sécurité)
- Notifications — signature HMAC sur les webhooks sortants (forward-compat intégrateurs)
- Notifications — retry unique sur Discord 429 (Retry-After cap 5 s)
- Notifications — log structuré sur échec Imgur (statut + extrait, pas de secret)
- Logs — filtre global de rédaction (mots de passe, tokens, JWT, webhooks)
- Connexion — succès journalisés avec user_id (échec garde l'identifiant pour audit)
- API — handler global d'erreur masque la query string (jamais de secret en log)
- Base de données — chat anonymisé (et non effacé) à la suppression du compte
- Base de données — colonnes utilisateur préparées pour la suppression différée
- Confidentialité — paramètres préchargés (désactivés par défaut)
- Confidentialité — export ZIP, suppression différée et annulation (mode opt-in)
- Utilisateurs — filtre « en attente de suppression » et annulation côté admin
- Planificateur — purge quotidienne des comptes en attente (opt-in, désactivé par défaut)
- Confidentialité — section admin (interrupteur, éditeurs FR/EN, liste comptes en attente)
- Confidentialité — paramètres préchargés (désactivés par défaut)
- Confidentialité — export ZIP, suppression différée et annulation (mode opt-in)
- Utilisateurs — filtre « en attente de suppression » et annulation côté admin
- Planificateur — purge quotidienne des comptes en attente (opt-in, désactivé par défaut)
- Confidentialité — section admin (interrupteur, éditeurs FR/EN, liste comptes en attente)
- Confidentialité — onglet utilisateur (politique, export, suppression différée) et bandeau de grâce


### Fixed
- Tableau de bord — widget Activité : labels sur plusieurs lignes en fenêtre étroite (plus de troncature)
- Tableau de bord — boutons Reset/Terminé compacts en desktop (taille tactile préservée sur mobile)
- Tableau de bord — widget Activité portail : chiffres centrés, plus de débordement en fenêtre étroite
- Tableau de bord — barre Personnaliser : boutons à droite, Reset rouge, sans icônes, lecture sur une ligne
- Classement — flèche d'évolution séparée du pseudo (troncature propre sur les noms longs)
- Portail — jaquettes plus compactes en mobile, tap sur la carte ouvre la fiche (boutons d'action retirés sur tactile)
- Reconnexion — logo de l'overlay toujours affiché pendant un redéploiement, déconnexion automatique si l'application a été mise à jour pendant la coupure
- Planificateur — bouton « Lancer maintenant » sur tâches obsolètes ne renvoie plus d'erreur (nettoyage automatique au démarrage)
- Suivi / Manquants — séries dupliquées affichées une seule fois (dédoublonnage par identifiant TMDB)
- Suppression d'utilisateur — contenus communautaires anonymisés au lieu d'être effacés
- PWA — URLs portail alignées, nom système unifié, icône maskable corrigée
- PWA — icônes Android avec fond opaque sur toutes les variantes (plus de carré blanc)
- Confidentialité — onglet anglais affichait la clé brute (traduction manquante restaurée)
- Base de données — contraintes manquantes sur `seen_alerts` et `xp_ledger`
- Connexion — icône GitHub restaurée avec le bon lien, ligne version texte retirée
- Force fin de ligne LF sur scripts et auto-fix CRLF au build Docker
- UX : padding crédits, lien GitHub login dédupliqué, retrait mention container
- Corrige les titres Discord affichés en texte brut au lieu de liens
- Portail — corrige le 500 quand le portail envoie un tmdb_id texte
- Utilisateurs — compte admin local marqué « Local » et plus comme source Emby
- Utilisateurs — date de dernière connexion admin renseignée à chaque login MK
- Utilisateurs — bandeau de stats actualisé immédiatement après désactivation/changement
- Utilisateurs — drawer ne se ferme plus au clic en dehors (uniquement par la croix)
- Utilisateurs — fin d'accès affichée en heures/minutes quand il reste moins de 24h
- Utilisateurs — colonne Statut en vert/rouge selon l'état du compte
- Utilisateurs — date de début d'accès pré-remplie avec la date de création du compte
- Utilisateurs — onglet Audit traduit et résumé en clair (rôle, identité, période, permissions)
- Utilisateurs — onglet Trophées : icônes Lucide réelles sans effets d'animation
- Utilisateurs — picto calendrier visible sur les champs date (icône blanche)
- Utilisateurs — bouton « Forcer la déconnexion » précise qu'il ne touche pas Emby
- XP — un compte inactif peut maintenant cumuler XP si l'admin coche « XP hors-ligne »
- Utilisateurs — onglet Trophées affiche les noms traduits (Cinéphile, Globe-Trotter…) au lieu des clés brutes
- XP — attribution post-session ne crashait plus en MissingGreenlet (sessions ORM expire_on_commit côté collector + scheduler)
- XP — durée de visionnage clampée au runtime (une longue pause ne fait plus dépasser les 85% artificiellement)
- XP — bandes-annonces, MusicVideo, LiveTV et autres types non Movie/Episode ne donnent plus d'XP
- XP — table d'actions nettoyée des entrées fantômes (complete_series, request_approved, event_*, streak_*) couvertes en réalité par les trophées
- Debug admin — bouton « Re-vérifier tous les trophées » : rattrape les trophées d'historique pour les utilisateurs qui n'ont pas joué depuis le fix
- Trophées — Marathonien Ultime relevé à 24h en une session (au lieu de 12h)
- Classement — avatar custom respecté dans les listes (leaderboard, ranking, daily digest, demandes), fallback initiale si l'image ne charge pas
- Sessions Emby — durée réelle utilisée (clamp wall/position/runtime), plus de fausses sessions de 24h+ après un redémarrage du collecteur
- Sessions Emby — fin de session marquée à la dernière apparition Emby (`last_seen_at`), pas au moment où le collecteur la détecte stale
- Debug admin — bouton « Réinitialiser un trophée pour tous » (suppression + remboursement XP) pour nettoyer un trophée mal attribué
- Utilisateurs — onglet Trophées : badge rareté (Commun → Mythique) + XP gagné affichés sous chaque trophée débloqué
- Profil — classement du mois affiche les 15 lignes sans scroll interne (la carte s'allonge selon le contenu)
- Migrations — chaînage 029 → 030 corrigé (deux heads Alembic résolus)
- Doublons — onglet Ignorés en lignes compactes groupées par série, header avec bouton « Tout restaurer »
- Portail — pastille de disponibilité unifiée (cache canonique prioritaire, plus de divergence entre Top 20 et autres listes)
- Portail — bouton « Lecture » retiré des bannières héros (héros redevient informatif, demande conservée)
- Portail — vidéo héros collée sous la topbar à toutes les largeurs (fin du masque qui découvrait le fond)
- Notifications admin — messages longs s'affichent sur plusieurs lignes au lieu d'être tronqués

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
