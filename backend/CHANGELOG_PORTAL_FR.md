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
- Jaquettes — durée du film ou série affichée au survol partout.
- Jaquettes — note TMDB (étoile dorée) affichée au survol.
- Jaquettes — titre, date et note affichés sous la vignette sur mobile.
- Préférences — option « Par défaut » : la langue suit le défaut du portail.
- Problèmes — navigation par pages avec choix du nombre affiché (10/25/50/100).
- Listes — bouton « Charger plus » pour voir au-delà de 50 titres.
- Listes — onglet « Public » : « Charger plus » au-delà de 50 listes.
- Notifications — bouton « Charger plus » pour voir les anciennes notifications.
- Soutien — cœur d'en-tête ouvrant le lien de don du serveur (si configuré).

### Changed
- Notifications — celles de plus de 6 mois supprimées automatiquement.
- Fiche média — couleur de la note TMDB harmonisée en doré.
- Avatars — anneau légendaire (niv. 50) : arc-en-ciel animé sur toutes les surfaces.
- Préférences — le réglage « masquer le contenu adulte » déplacé ici, sous les genres.
- Accueil — Populaires et Mieux notés viennent désormais de Découvrir.
- Quoi de neuf — les nouveautés restent jusqu'à votre prochaine visite.
- Notifications — marquées lues à la fermeture du panneau (surbrillance conservée à l'ouverture).
- Formulaires — champs aux coins plus nets, distincts des filtres arrondis.

### Fixed
- Invitations — les profils privés et les admins ne peuvent plus être invités.
- Notifications — navigation clavier (Échap pour fermer) et fin des doublons au chargement.
- Notifications — surbrillance des non-lues suit la couleur d'accent de votre thème.
- Reprendre la lecture — affiche uniquement vos titres en cours.
- Demandes — refusées (au lieu d'être laissées passer) si la vérification adulte ne joint pas TMDB.
- Listes — l'historique des collaborateurs affiche les pseudos, jamais les logins Emby.
- Jaquettes — durée d'un titre à venir affichée dès que TMDB la publie.
- Accueil — bandeau vedette : un titre déjà demandé affiche « En attente ».
- Demandes — les demandes de film en un clic affichent succès ou refus.
- Mode maintenance — le portail est désormais entièrement verrouillé (page d'attente seule).
- Surprise — titre et synopsis du tirage affichés dans votre langue.
- Accueil — titres et synopsis des carrousels affichés dans votre langue.
- Paramètres — couleurs de votre rang appliquées dès l'ouverture (plus de flash).
- Salle ciné — bouton « Lancer » centré sur l'écran, ouverture Emby fiabilisée.
- Salle ciné — bande-annonce reprend au retour de l'onglet Emby.
- Salle ciné — décompte d'intro synchronisé avec le compte à rebours.
- Salle ciné — plus de requêtes en boucle après avoir quitté la salle.
- Demandes — titres affichés dans votre langue.
- Fiche média — lien TMDB ouvre dans la langue de l'app.
- Dates affichées dans votre langue (au lieu de celle du navigateur).
- Découvrir — listes (tendances, populaires, etc.) affichées dans votre langue.
- Changelog — versions sans nouveauté masquées (plus de cartes vides).
- Avatars personnalisés affichés dans les contributeurs de listes et le sélecteur d'utilisateurs.
- Pastilles « déjà demandé » affichées sur les grandes listes.
- Quoi de neuf — barre XP pleine au niveau max (sans niveau 51).
- Quoi de neuf — un ajout du jour reste visible même après fermeture de l'overlay.
- Recommandés pour vous — le carrousel d'accueil affiche 20 titres distincts.
- Contenu adulte — le masquage s'applique à toutes les listes, recherche et recommandations.
- Demandes — les titres adultes ne sont demandables que si l'administrateur l'autorise.
- Notifications — messages admin et notifs de listes affichent un libellé lisible.
- Soirée ciné — événement privé : capacité suivie des invités (sélecteur masqué).
- Erreurs réseau — message clair affiché au lieu d'une liste vide trompeuse.

## [1.0.0-rc.4] - 2026-05-30

### Changed
- Avatars — anneau coloré par niveau (bronze → légendaire) partout.
- Soirée ciné — avatars des sièges au style du classement.

### Fixed
- Bandeau événements — lisible (statique) en mode mouvement réduit.
- Pastille Dispo — plus de clignotement quand l'index rattrape son retard.
- Affiches de la home — plus de vignettes cassées au premier chargement.
- Navigation — pastilles de disponibilité et de demande chargent même en défilement rapide.

## [1.0.0-rc.3] - 2026-05-22

## [1.0.0-rc.2] - 2026-05-22

## [1.0.0-rc.1] - 2026-05-21

### Added
- Salle de cinéma — vue mobile dédiée (grille avatars 3 colonnes).
- Salle de cinéma — progression par participant, tag « En retard ».
- Salle de cinéma — présence temps réel (sièges libérés à la déconnexion).
- Salle de cinéma — timer de lecture en direct pour tout événement.
- Soirées ciné — capacité par événement choisie à la création (5/10/15/20).

### Changed
- Pied de page — bandeau d'attribution retiré (crédits conservés sur la page Crédits).
- Unification visuelle des jaquettes (toutes surfaces) avec retrait PEGI sur fiche détail
- Accueil : rythme des listes uniformisé (titres aérés, jaquettes serrées).
- Sous-titres — bibliothèque : 3 jaquettes par ligne sur mobile.
- Page détail — densification mobile (plus d'info sur petit écran).
- Page détail — retrait du bandeau « Disponible sur Emby » (info redondante).
- Page détail — sidebar premium (icônes, pastille statut, libellés capitalisés).
- Découvrir — grille resserrée sur mobile (auto-fit + clamp).
- Page personne — hero responsive (photo + titre adaptés au mobile).
- Jaquettes mobile : actions retirées, clic direct sur la fiche.
- Accueil mobile : synopsis des héros masqués pour aérer.
- Accueil — héros : diaporama d'images (10 s, fondu enchaîné).
- Quoi de neuf — overlay affiché une seule fois par jour (bouton Fermer suffit).
- Listes — 3 jaquettes par ligne sur mobile, espace resserré.
- Salle de cinéma — sièges dynamiques centrés, badge « Complet ».
- Salle de cinéma — sièges affichent avatar + pseudo, panneau marathon repositionné.
- Salle de cinéma — bouton « Lancer » toujours cliquable, intro synchronisée.

### Fixed
- Soirées ciné : événements passés verrouillés (salle fermée, accept bloqué, pastille « Terminé »).
- Choix du pseudo : modal ré-armé à chaque connexion, overlays masqués jusqu'à validation.
- Accueil : rafale de toasts « Trop de tentatives » supprimée au chargement
- Jaquettes : restauration contour blanc + médailles Top 3 (or/argent/bronze).
- Jaquettes : durée affichée au survol (cache TMDB pour le Top 20).
- Jaquettes : tooltips dates restaurés sur tous les rubans diagonaux.
- Jaquettes : correction panel coincé après clic sur statut « Demandé ».
- Jaquettes : animation pulse « Nouveau » rendue fluide (GPU).
- Page détails : ruban de statut et chip disponibilité alignés sur le portail.
- Jaquettes : tooltip du bouton signet renommé en « Ajouter à une liste ».
- Hero Emby : titre réduit sur mobile pour libérer la zone vidéo.
- Hero Emby : jaquettes mobile à hauteur normale (plus d'espace mort).
- Navigation mobile : « Mon profil » remonté en 2ème position.
- Demandes — message d'erreur clair quand la demande échoue (quota, doublon, blacklist).
- Jaquettes mobile : pastille disponibilité repositionnée (plus de chevauchement).
- Fiche personne — badge statut des demandes à nouveau visible sur la filmographie.
- Recherche — refonte live TMDB avec cache 5 min (jaquettes toujours fraîches).
- Fiche détail — langue et pays traduits dans la langue de l'interface.
- Fiche détail — langue originale lue depuis TMDB (au lieu première piste).
- Accueil — bandes-annonces héros : officielles + récentes prioritaires (meilleure VF).
- Accueil — changement manuel de slide héros : compteur 10 s réinitialisé.
- Accueil — bandes-annonces héros : lecture à la demande, plus d'auto-play en fond.
- Préférences — barre Enregistrer reste visible après changement de langue ou genre.
- Préférences — synopsis, recommandations et bandes-annonces rechargés à la nouvelle langue.
- Préférences — onglets sticky : retrait du flou qui parasitait les cartes.
- Salle de cinéma — s'adapte à toute taille d'écran sans scroll vertical.
- Salle de cinéma — URL bloquée aux non-invités, audio coupé après l'intro.

## [0.3.0] - 2026-05-14

### Added
- Pages publiques de profil — carte, bio, genres et trophées accessibles depuis le classement
- Bouton « Voir mon profil public » pour prévisualiser exactement ce que voient les autres
- Profil — alias anonyme « Utilisateur 1234 » tant qu'aucun pseudo n'est défini
- Pseudo personnalisé — choix obligatoire à la première connexion, contrôle de disponibilité, modifiable tous les 6 mois
- Pseudos réservés (« admin », « administrateur », « administrator », « root »)
- Avatar personnalisé — importez votre image (5 Mo max), retour à l'avatar par défaut possible
- Aperçu en direct des titres et cosmétiques d'avatar avant validation
- Page Paramètres premium en 5 onglets (identité, apparence, préférences, visibilité, compte)
- Paramètres — onglet Compte affiche la date d'expiration (ou « Aucune limite »)
- Connexion — page d'identification dédiée au portail
- Connexion — indicateur de série de connexions et lien direct pour le mot de passe
- Salle de cinéma — marathon : avancement temps réel, film suivant verrouillé à 85 %
- Recherche — suggestions instantanées, recherches récentes, navigation clavier, raccourci Ctrl/Cmd+K
- Tickets — choix précis du film, série, saison ou épisode au signalement (ou hors médias)
- Tickets — page de détail repensée : aperçu visuel, avatars, badge admin, statut clair
- Tickets — fermeture auto après 7 jours d'inactivité, alerte admin à l'ouverture, filtres statut/source/type
- Centre d'aide intégré au menu avatar — 15 articles classés, recherche, lecteur plein écran
- Aide modifiable par les administrateurs — éditeur riche, sauvegarde auto, brouillons, corbeille 30 jours
- Chat — compteur de messages non lus persistant, historique chargé à l'ouverture, connexion temps réel maintenue
- Chat — bouton signalement animé puis verrouillé après envoi
- Notifications — admins et modérateurs voient les messages de chat signalés
- Notifications — un administrateur peut envoyer un message ciblé qui apparaît dans la cloche
- Classement mensuel — tous les utilisateurs visibles, comptes locaux et désactivés exclus
- XP et trophées cumulés dès l'activation du compte par un administrateur
- Trophées — 14 nouveaux trophées débloquables (sociaux, marathons, classiques, surprises)
- Trophées listes — deux familles Curateur et Bibliothécaire (5 paliers chacune)
- Crédits — nouvelle page partenaires accessible depuis le pied de page
- Mention légale ajoutée en pied de page
- Page introuvable — vraie 404 accessible avec retour au portail
- Accessibilité — lien « Aller au contenu principal » au focus clavier

### Changed
- Classement — refonte premium showcase : hero champion du mois, bandeau stats, top 100, podium enrichi
- Classement — avatar du 1er ne tourne plus, anneau or statique
- Cartes média — ruban diagonal « Disponible » retiré (le point vert suffit)
- Avatars — fond intérieur aligné au fond de page, silhouette plus présente, icône en remplacement de la lettre
- Crédit TMDB — bandeau compact sur une ligne, padding réduit
- Notifications — icônes harmonisées en lieu et place des emojis
- Accueil et profil — espacement réduit sur mobile
- Salle de cinéma — enchaînement de bandes-annonces avec transition noire, bouton Infos sur le trailer en cours
- Salle de cinéma — jaquette affichée à l'écran après le compte à rebours
- Demandes — auto-nettoyage des demandes disponibles après un délai (réglé par l'admin)
- Listes — pseudos anonymisés côté propriétaire et contributeurs
- Paramètres — onglet actif synchronisé avec l'URL (lien direct et refresh)
- Quoi de neuf aujourd'hui — Top 3 du mois aligné sur le widget Classement, votre position en 4ᵉ ligne hors podium
- Tickets — filtres allégés (pills statut, type, tri), filtre Source retiré
- Tickets — raccourci « Mes tickets » retiré du menu avatar (doublon de l'onglet Problèmes)
- URLs standardisées (anciens favoris à recréer)
- Barre du haut — roue crantée retirée (configuration côté admin)
- Barre du haut — bouton Tableau de bord devient une icône maison à droite des notifications
- Barre du haut — onglets décalés du logo
- Notifications — ouvrir la cloche marque tout comme lu (bouton « Tout marquer » retiré)
- Onglets internes harmonisés sur le style glass du reste de l'app
- Barre de navigation mobile — onglet actif encadre icône + libellé, onglet « Listes » ajouté
- Barre du haut mobile allégée — Tableau de bord, Listes, Calendrier, Administration regroupés dans le menu avatar
- Profil mobile — carte d'identité compactée (largeur, paddings, avatar réduits)
- Profil — halos tournants et pulsation brumeuse retirés (visuel allégé)
- Trophées — pulsation brumeuse retirée des cartes (halo coloré statique conservé)
- Voir tous les trophées — animations résiduelles retirées des lignes
- Trophées — XP de récompense réduit pour lisser la progression (XP déjà cumulé ajusté)

### Fixed
- Accueil — image de fond visible quand la bande-annonce ne démarre pas (au lieu d'un écran noir)
- Accueil — bandes-annonces : fondu noir cinématique entre deux trailers, prochain pré-chargé
- Accueil — taper la bande-annonce active/coupe le son (bouton son retiré)
- Hero « Récemment ajouté » — bande-annonce opaque en plein cadre, transitions alignées sur le hero principal, dégradés fondus avec la barre du haut
- Hero « Récemment ajouté » — bouton « Plus d'infos » désormais visible (rendu cassé corrigé)
- Hero « Récemment ajouté » — fin de bande-annonce passe au film suivant au lieu de boucler
- Mobile — barre du haut toujours opaque, nom « MediaKeeper » désormais affiché à côté du logo
- Mobile — espace réduit accueil, dropdown cloche non tronqué, crédit TMDB wrap propre
- Mobile — boutons demander, lecture, re-demander et ajout liste toujours visibles sur les jaquettes
- Mobile — voir tous les trophées en cartes compactes, tap pour déplier les détails
- Mobile — grille des trophées du profil limitée à 2 lignes par page (fluidité préservée)
- Mobile — effet d'avatar « couronne divine » et profil légendaire optimisés
- Quoi de neuf aujourd'hui — avatars et images remplissent leur cercle sur mobile, taille réduite sur grands écrans
- Quoi de neuf aujourd'hui — barre de défilement stylisée (gradient accent, fin du slab blanc)
- Modale Signaler un problème — dropdown média se ferme au clic ailleurs
- Profil public — avatar sans photo affiche l'icône silhouette
- Profil public — barre XP affiche le seuil du niveau suivant (au lieu du courant)
- Profil privé — page dédiée au lieu d'une erreur générique depuis le classement
- Toast trophée — ne se ré-affiche plus à chaque refresh
- Surprends-moi — erreurs intermittentes 500 sur clics rapides successifs corrigées
- Recherche — jaquettes des résultats s'affichent désormais correctement
- Carrousels — card « Voir plus » a les mêmes coins arrondis que les jaquettes adjacentes
- Page détails média — page ouverte en haut systématiquement
- Modale pseudo — plus de texte qui fuit en bas à gauche pendant la transition
- Demandes — passage automatique à « Disponible » et notification dès l'arrivée du média
- Top du mois — séries comptées 1 fois par utilisateur (plus de gonflage par épisodes)
- Top genres — chaque série compte une fois par genre
- Top du mois et genres — visionnages comptés à partir de 85 % de la durée
- Trophées — déblocage immédiat sur chat, demandes, tickets, avatar, événements
- Trophées — pourcentage global aligné sur les seuls trophées atteignables
- Tableau de bord — raccourci masqué pour les modérateurs sans accès backoffice
- Pastille de disponibilité — séries complètes ne s'affichent plus en « partiellement disponibles » après ré-import
- Articles d'aide — modifications conservées pendant la frappe
- Chat — salon par défaut créé automatiquement, fil fonctionnel dès la première ouverture
- Titres d'onglet du navigateur corrigés sur les pages Demandes
- Page Changelog — fond aligné sur le reste du module
- Popups cloche et calendrier — repositionnés juste sous l'icône sur grands écrans
- Barre du haut — rayon des coins du bouton calendrier et recherche aligné sur les autres icônes
- Liste des demandes admin — action sur une ligne ne renvoie plus en haut
- Création d'événement — clic à côté ne ferme plus la fenêtre, recherche limitée aux titres en bibliothèque
- Bandeau d'événement à venir — fond transparent, texte plus discret, collé sous la barre du haut
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
