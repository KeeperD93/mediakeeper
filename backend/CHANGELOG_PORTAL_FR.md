# Changelog Portal

<!--
Changelog destiné aux utilisateurs du Portal (partie publique).
Ne pas y mentionner les changements strictement admin / backoffice — ceux-ci
vont dans CHANGELOG_FR.md. Un changement qui touche les deux surfaces doit
apparaître dans les deux fichiers.

Section [Unreleased] : on accumule ici les modifications visibles côté viewer
au fil du temps. Quand on décide de publier, on remplace `[Unreleased]` par
`[x.y.z] - YYYY-MM-DD` et on met à jour PORTAL_VERSION dans
backend/api/portal_changelog.py.
Cette section est volontairement sans date pour ne pas être affichée aux
utilisateurs.
-->

## [Unreleased]

### Added
- Accessibilité — lien « Aller au contenu principal » au focus clavier
- Page introuvable — vraie page 404 accessible avec retour au portail (plus de redirection silencieuse)
- Trophée « Pause Pipi » — débloquable (5 pauses de 2 à 5 minutes)
- Trophées « Pilote » et « Le Retardataire » — débloquables
- Trophées « Nuit Blanche Ultime », « No Life », « Le Roi » — débloquables
- Trophées « Le Solitaire » et « Le Synchronisé » — débloquables
- Trophées « Voyageur temporel », « Le Classique », « Le Puriste » — débloquables
- Trophées « Coup de chance » — débloquables via l'utilisation du bouton Surprends-moi (4 paliers)
- Crédits — nouvelle page (TMDB, OpenSubtitles, Emby, Imgur, YouTube) accessible depuis le pied de page
- Paramètres — onglet Compte affiche la date d'expiration du compte (ou « Aucune limite »)
- Notifications — admins et modérateurs voient les messages de chat signalés dans la cloche
- Chat — bouton signalement animé puis verrouillé après envoi (impossible de re-signaler)
- Tickets — choix précis du film, de la série, d'une saison ou d'un épisode au moment de signaler un problème (ou d'un sujet hors médias), avec recherche directe dans la bibliothèque
- Tickets — page de détail et conversation entièrement repensées : aperçu visuel du média, avatars, badge admin, statut clair, expérience mobile soignée
- Tickets — fermeture automatique au bout de 7 jours sans activité, alerte aux admins dès l'ouverture d'un nouveau ticket, filtres par statut, source et type de problème
- Page Paramètres premium repensée en 5 onglets : identité, apparence, préférences, visibilité, compte
- Avatar personnalisé : importez votre propre image, elle remplace celle d'Emby (5 Mo max, retour à Emby possible à tout moment)
- Pseudo MediaKeeper : choix obligatoire à la première connexion, vérification en direct de la disponibilité, suggestions auto si déjà pris, modifiable une fois tous les 6 mois
- Profil public consultable : cliquez sur un nom dans le classement pour voir sa carte, bio, genres et trophées débloqués
- Bouton « Voir mon profil public » pour visualiser exactement ce que les autres voient
- Aperçu en direct des titres et cosmétiques d'avatar avant validation
- Indicateur de série de connexions et lien direct vers Emby pour le mot de passe
- XP et trophées cumulés dès l'activation du compte par un administrateur, sans avoir besoin d'ouvrir le portail au préalable
- Pseudos « admin », « administrateur », « administrator » et « root » réservés
- Classement mensuel — tous les utilisateurs Emby visibles (admins et modérateurs inclus), comptes locaux et désactivés exclus
- Centre d'aide intégré au menu avatar : 15 articles classés par catégories, barre de recherche, ouverture en plein écran
- Aide modifiable par les administrateurs : éditeur de texte riche, sauvegarde automatique, brouillons, corbeille avec restauration sous 30 jours
- Chat — compteur de messages non lus persistant (badge sur le bouton + replié et sur l'icône chat déplié), historique complet chargé à l'ouverture, connexion temps réel maintenue tant que le portail est ouvert
- Notifications — un administrateur peut envoyer un message ciblé qui apparaît dans la cloche
- Mention légale ajoutée en pied de page
- Trophées listes — deux nouvelles familles (Curateur, Bibliothécaire) avec 5 paliers chacune

### Changed
- Quoi de neuf aujourd'hui — Top 3 du mois aligné sur le widget Classement du dashboard (visuel identique, votre position ajoutée en 4ᵉ ligne quand vous êtes hors podium)
- Tickets — filtres restructurés en groupes labellisés (statut, source, problème) au style pill du module Demandes
- URLs standardisées (anciens bookmarks à refaire)
- Barre du haut : roue crantée retirée — la configuration se gère désormais depuis MediaKeeper
- Barre du haut : bouton « Tableau de bord » devient une icône maison sans texte, repositionnée à droite des notifications
- Barre du haut : onglets légèrement décalés du logo MediaKeeper
- Notifications : ouvrir la cloche marque automatiquement toutes les notifications comme lues (bouton « Tout marquer lu » supprimé)
- Onglets des pages internes (fiche média, personne, listes, admin) harmonisés sur le même style glass que le reste de l'app
- Barre de navigation mobile : l'onglet actif encadre désormais icône + libellé (plus de surlignage limité à l'icône)
- Barre du haut mobile allégée : Tableau de bord, Listes, Calendrier et Administration regroupés dans le menu avatar — ne restent dans la barre que recherche, notifications et avatar
- Profil mobile : carte d'identité compactée (largeur, paddings et avatar réduits) pour gagner en place
- Profil : halos tournants et pulsation brumeuse autour de la carte retirés (visuel allégé, sur tous les écrans)
- Trophées : pulsation brumeuse retirée des cartes (halo coloré conservé en statique)
- Voir tous les trophées : animations résiduelles retirées des lignes (progress shine, couronne master, badge xmas)
- Trophées : XP de récompense réduit pour lisser la progression (XP déjà cumulé ajusté en conséquence)

### Fixed
- Trophées — déblocage immédiat sur chat, demandes, tickets, avatar, événements (plus d'attente de la prochaine connexion)
- Trophées — pourcentage global de progression aligné sur les seuls trophées atteignables
- Tableau de bord — raccourci masqué pour les modérateurs sans accès backoffice (plus de clic qui rebondit aussitôt)
- Pastille de disponibilité — séries complètes ne s'affichent plus en « partiellement disponibles » après un ré-import Emby (fusion des doublons d'index, purge auto des orphelins au prochain scan)
- Quoi de neuf aujourd'hui — barre de défilement stylisée (gradient accent + piste discrète, plus de slab blanc)
- Profil public : barre XP affichait le seuil du niveau actuel au lieu du suivant (ex. « 1500/1500 » alors qu'il fallait « 1574/2100 »)
- Articles d'aide — modifications conservées pendant la frappe (plus de retour à la version précédente)
- Chat — salon par défaut créé automatiquement, fil de discussion fonctionnel dès la première ouverture
- Quoi de neuf aujourd'hui — taille de l'overlay réduite sur grands écrans (panel plus compact, hero allégé)
- Voir tous les trophées (mobile) : cartes compactes par défaut (icône, nom, rareté, description, progression), tap pour déplier et révéler les détails (étoiles, XP, date, récompenses, bouton épingler)
- Profil mobile : grille des trophées limitée à 2 lignes par page pour rester fluide quand beaucoup d'effets sont débloqués
- Profil : effet d'avatar « couronne divine » optimisé pour rester fluide sur téléphone
- Profil legendary (niveau 50) : carte allégée sur mobile (étoiles et embers réduits) pour rester fluide
- Titres d'onglet du navigateur corrigés sur les pages du module Demandes
- Page Changelog : fond aligné sur le reste du module Demandes (plus de bande sombre sans teinte)
- Popups cloche et calendrier : repositionnés juste sous l'icône sur les grands écrans
- Barre du haut : rayon des coins du bouton calendrier et du bouton recherche (mobile) aligné sur les autres icônes
- Liste des demandes admin : une action sur une ligne ne renvoie plus en haut de la liste
- Création d'événement : un clic à côté de la fenêtre ne la ferme plus (fermeture uniquement via la croix ou Annuler)
- Création d'événement : la recherche de film/série ne propose plus que les titres effectivement présents dans la bibliothèque
- Bandeau d'événement à venir : fond transparent, texte plus discret, collé sous la barre du haut
- Bande-annonce d'accueil : fondu noir cinématique entre deux bandes-annonces, sans passage par l'image de fond et avec pré-chargement de la suivante
- Mobile : boutons demander, lecture, re-demander et ajout liste désormais toujours visibles sur les jaquettes (plus besoin de survol)
- Mobile : hero « Récemment ajouté sur Emby » désormais affiché, bande-annonce opaque en plein cadre avec dégradé sombre sous les infos et boutons
- Mobile : hero « Récemment ajouté sur Emby » — taper la bande-annonce active/coupe le son, bouton son retiré (même comportement que la hero principale)
- Hero « Récemment ajouté sur Emby » : image de fond conservée pendant les transitions entre bandes-annonces (plus de flash transparent)
- Hero « Récemment ajouté sur Emby » : transitions entre bandes-annonces alignées sur la hero principale (fondu noir avant, chargement caché, fondu noir vers la suivante, filet de sécurité 4 s)
- Hero « Récemment ajouté sur Emby » : dégradés haut et bas alignés sur la couleur du fond de la page pour fondre les jonctions avec la barre du haut et la rangée de jaquettes en dessous, hauteur du bloc augmentée pour compenser la zone assombrie
- Hero « Récemment ajouté sur Emby » : icône du bouton « Plus d'infos » désormais visible (rendu cassé corrigé)
- Hero « Récemment ajouté sur Emby » : avec le son activé, la fin d'une bande-annonce bascule désormais sur le film suivant au lieu de relancer la même en boucle
- Mobile : bande-annonce d'accueil opaque pendant les transitions (plus de flash de transparence laissant voir le fond de la page entre deux trailers)
- Mobile : barre du haut toujours opaque (plus de transparence variable selon le scroll, et plus de transparence quand une bande-annonce joue)
- Mobile : nom « MediaKeeper » désormais affiché à côté du logo dans la barre du haut
- Marque renommée « MediaKeeper » (K majuscule) partout dans l'interface

## [0.2.0] - 2026-04-20

### Added
- Overlay « Quoi de neuf aujourd'hui ? » : résumé quotidien du module Demandes avec nouveautés bibliothèque, événements à venir, classement du mois, quota de demandes, tickets ouverts, prochain trophée à décrocher et série de visionnages
- Menu avatar : nouvelle entrée « Quoi de neuf aujourd'hui ? » pour rouvrir le résumé à tout moment
- Admin demandes : saisie d'un motif au rejet d'une demande, affiché au survol du tag « Rejetée » côté utilisateur
- Listes de lecture personnelles : créer une liste, la rendre privée / publique / collaborative, ajouter les films et séries, exporter en JSON ou CSV, copier une liste publique, panneau déplié avec items, contributeurs et historique
- Nouveau bouton « Listes » dans la barre du haut, à droite du cœur
- Refonte visuelle premium des pages Demandes, Listes et Problèmes : rangées pleine largeur avec arrière-plan du média, barre de statut animée, avatar du demandeur, numérotation, filtres par type (films / séries), action rapide approuver / refuser / supprimer en icônes
- Clic sur la jaquette dans la liste des demandes ouvre la fiche du média
- Bouton « copier le titre » au survol des rangées
- Jaquettes : bouton « Ajouter à une liste » au survol, accroché au bord droit
- Fiche détaillée d'un média : bande-annonce YouTube inline dans le hero (plus de lightbox), nouveaux carrousels « Par le réalisateur », « Avec l'acteur principal » et « Dans la même franchise »
- Nouvelles pages Personne (filmographie filtrable réalisation / interprétation) et Franchise (liste ordonnée des films de la saga), accessibles depuis les crédits d'une fiche

### Changed
- Jaquettes : tags d'état affichés en bandeau diagonal, palette recalibrée (bronze, ardoise, indigo, émeraude, rouille)
- Accueil : chargement plus rapide, chaque rangée apparaît dès qu'elle est prête au lieu d'attendre la plus lente
- Onglet « À voir aussi » : section « Titres similaires » retirée (peu pertinente sur les nouveautés), recommandations étendues à 20 titres
- Demande supprimée par un admin : l'utilisateur peut immédiatement la soumettre à nouveau
- Refonte complète de la fiche détaillée : hero plein écran avec affiche, logos studios, score et popularité, certification d'âge, onglets Vue d'ensemble / Distribution / Extras & avis / À voir aussi
- Fiche détaillée enrichie : mots-clés, plateformes de streaming (FR), équipe clé (scénario, musique, photo, montage, production), équipe étendue (20 rôles), avis utilisateurs, extras (bande-annonces, teasers, making-of, coulisses), liens TMDB / IMDb / site officiel, bannière saga dédiée
- Tag « Rejeté » passé au rouge pour mieux se distinguer du tag « Demandée », libellé au masculin sur les jaquettes
- Menu avatar : entrée « Quoi de neuf » renommée « Changelog »

### Fixed
- Profil : section « Mes listes » désormais peuplée (elle restait vide à cause d'une erreur silencieuse)
- Export CSV d'une liste : colonnes titre, année et date d'ajout, fichier nommé d'après la liste
- Fiche média : bande-annonce affichée dans l'ordre langue utilisateur → anglais → langue originale, plus jamais manquante sur les titres étrangers
- Fiche média : synopsis affiché en anglais quand aucune traduction française n'existe, au lieu de « Aucun synopsis disponible »
- Items des listes : affiche, titre et année visibles (plus uniquement l'identifiant TMDB)
- Historique d'une liste : le titre du média ajouté ou retiré s'affiche désormais entre guillemets
- Tag diagonal d'état (« Rejetée x3 », « En cours »…) : contenu centré dans le bandeau, plus de débordement vers le bord de l'affiche
- Accueil : bandeaux diagonaux « Rejetée » et « Validée » affichent à nouveau leur libellé (ils apparaissaient vides)
- Bandeau « Rejetée xN » : libellé recentré quand le compteur x2/x3 est présent
- Jaquettes de l'accueil : les demandes rejetées affichent désormais le tag « Rejetée » et le bouton « Re-demander » (au lieu de repasser à « Demander » comme si rien ne s'était passé)
- Carrousels de la fiche détaillée (Distribution, Recommandations, Par le réalisateur, …) maintenant parfaitement alignés à gauche
- Barre d'onglets de la fiche média : ne reste plus figée en haut au scroll
- Profil : le bouton « Re-demander » d'une demande refusée ouvre désormais l'overlay de demande et passe en « Demandée » une fois la resoumission validée
- Fiche média : le bouton « Ajouter à une liste » ouvre un overlay avec les listes existantes (plus la page dédiée)
- Profil : carte « Vos genres » plus dense en Full HD — les tuiles internes (jour préféré, marathon, ratio…) s'affichent désormais en colonnes au lieu de s'empiler verticalement, alignant la hauteur avec « Trophées »
- Alignement des carrousels : titre et première jaquette désormais parfaitement calés sur le même axe, sur toutes les rangées
- Onglet « À voir aussi » : carrousels désormais alignés pleine largeur comme sur l'accueil
- Cartes de l'onglet « À voir aussi » : pastille de disponibilité, bouton « Lancer » et tags (nouveauté, visionné…) affichés comme sur l'accueil
- Bloc Saga de la fiche média : mêmes cartes interactives (pastille, lancer, demander, tags) que sur l'accueil
- Fiche média : les statuts « Approuvée / Refusée / Demandée / Disponible » sont maintenant affichés en tag sur la jaquette (sous l'âge), plus en bouton désactivé
- Fiche média : statut technique (« Returning Series », « Post Production »…) traduit en français

## [0.1.0] - 2026-04-18

### Added
- Popup « Quoi de neuf ? » dédié au viewer Demandes, distinct de celui de l'admin
- Bouton « Re-demander » sur les demandes refusées + badge x2/x3 indiquant le nombre de soumissions

### Changed
- Messages d'erreur du backend traduits côté interface plutôt qu'affichés en dur

### Fixed
- Statut d'une demande mis à jour instantanément après action admin sur toutes les pages
- Disponibilité d'un titre récemment ajouté refletée sous 1 minute au lieu de nécessiter un rechargement
- Quota mensuel et XP protégés contre la perte sous clics rapides
- Écran profil, bandes « Top année » et « À venir » chargent plus vite
- Page profil ne déborde plus horizontalement sur mobile quand les statistiques sont bien remplies
