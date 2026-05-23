<p align="center">
  <img src="frontend/public/assets/icons/mediakeeper_banner.png" width="640" alt="MediaKeeper">
</p>

<p align="center">
  <a href="README.md">English</a> · <b>Français</b>
</p>

<p align="center">
  <i>Compagnon open-source auto-hébergé pour votre médiathèque : tableau de bord, portail de demandes, trophées, doublons, manquants, statistiques, sous-titres et plus encore.</i>
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: GPL v3+" src="https://img.shields.io/badge/license-GPL%20v3%2B-blue.svg"></a>
  <a href="https://github.com/KeeperD93/mediakeeper/actions/workflows/backend.yml"><img alt="Backend CI" src="https://github.com/KeeperD93/mediakeeper/actions/workflows/backend.yml/badge.svg"></a>
  <a href="https://github.com/KeeperD93/mediakeeper/actions/workflows/frontend.yml"><img alt="Frontend CI" src="https://github.com/KeeperD93/mediakeeper/actions/workflows/frontend.yml/badge.svg"></a>
  <a href="https://github.com/KeeperD93/mediakeeper/actions/workflows/security.yml"><img alt="Security" src="https://github.com/KeeperD93/mediakeeper/actions/workflows/security.yml/badge.svg"></a>
  <a href="https://discord.gg/A2hyNUUn6a"><img alt="Discord" src="https://img.shields.io/discord/1507137232941617234?label=Discord&logo=discord&color=5865F2&logoColor=white"></a>
  <a href="https://ko-fi.com/keeperd93"><img alt="Ko-fi" src="https://img.shields.io/badge/Ko--fi-Soutenir-FF5E5B?logo=ko-fi&logoColor=white"></a>
  <img alt="AI-assisted" src="https://img.shields.io/badge/Assist%C3%A9%20IA-Oui-8A2BE2">
</p>

---

> [!WARNING]
> **En développement actif — pas encore stable.**
>
> MediaKeeper évolue sur la branche `v1.0.0-rc.x`, avant la première version stable `v1.0.0`.
> Attendez-vous à des changements de schéma, des refactorisations cassantes,
> des éléments manquants et quelques aspérités.
> Ne le pointez pas sur des données de production que vous ne pouvez pas vous
> permettre de perdre, et figez un tag d'image immuable (par ex.
> `ghcr.io/keeperd93/mediakeeper:v1.0.0-rc.3`) plutôt que `:latest` si vous
> voulez un comportement reproductible.

---

## Qu'est-ce que MediaKeeper ?

MediaKeeper est un **compagnon auto-hébergé en un seul container** pour une instance Emby. Il complète Emby avec deux surfaces dans une seule application :

- Un **back-office admin** soigné pour gérer votre bibliothèque, repérer les doublons, suivre l'activité, gérer les sous-titres, et bien plus encore.
- Un **portail utilisateur** convivial conçu pour les personnes avec qui vous partagez Emby — navigation dans le catalogue, demandes, trophées, listes, récap quotidien, actualités, tickets et soirées ciné partagées.

Tout tourne depuis un **seul container Docker** avec PostgreSQL 16 embarqué.

---

## Fonctionnalités clés

MediaKeeper étend Emby avec un back-office pour piloter l'instance et un portail qui offre aux utilisateurs une véritable expérience produit. Voici ce qui se distingue.

### Points forts

- **Soirées ciné partagées immersives** — planifiez des événements avec un cinéma virtuel.
- **Système de demandes intégré** — les utilisateurs demandent des films, séries ou saisons ; quotas, blacklist, auto-nettoyage et modération admin sont livrés clé en main.
- **Trophées & XP** — 160+ trophées répartis en familles (communauté, visionnage, marathons, secrets, jalons, listes), niveaux jusqu'à 50, classement mensuel.
- **Profils publics utilisateurs** — chaque utilisateur peut personnaliser un pseudo, un avatar, équiper des titres cosmétiques, et les autres peuvent consulter la version publique du profil.
- **Suivi utilisateurs** — gérez vos utilisateurs, ajustez les dates d'accès au serveur Emby, renseignez les informations de profil, suivez leurs statistiques…
- **Quoi de neuf aujourd'hui** — un overlay une fois par jour met en avant le Top 3 du mois et la position de l'utilisateur, les derniers ajouts, les actualités définies par l'admin…

### Back-office admin

Pensé pour l'opérateur qui maintient l'instance Emby vivante.

**Santé de la bibliothèque**

- **Tableau de bord** — stats en direct, santé des services, fil d'activité, agencement des cartes personnalisable (glisser-déposer, réordonnancement mobile via liste de titres)
- **Statistiques** — utilisateurs, bibliothèques, lectures, graphiques lisibles sur mobile
- **Santé des médias** — analyse automatique, regroupement par sévérité, jaquettes des incidents, lancement à la demande
- **Doublons** — règles de détection, historique, liste des ignorés, restauration, accès rapide en cache
- **Suivi (Watchlist)** — suivi des séries (saisons manquantes), tags langue audio sur les épisodes, règles de monitoring, scan configurable

**Gestion de fichiers**

- **Gestionnaire de médias** (desktop) — parcourir, déplacer, renommer avec l'aide de l'agent TMDB (API), taguer, dédupliquer directement sur le disque, sélection au lasso...
- **Sous-titres** — téléchargement des sous-titres par OpenSubtitles, suppression des langues et sous-titres déjà disponibles sur les fichiers…

**Utilisateurs & demandes**

- **Utilisateurs** — drawer 7 onglets (identité, accès, sécurité, activité, trophées, notes, audit), rôles & permissions granulaires (chat, demandes, problèmes, listes, XP hors-ligne), période d'accès avec prolongations rapides, suppression réversible, journal d'audit, notes admin, tags, export RGPD par utilisateur
- **Demandes premium** — recherche, filtres, vue table/cartes, actions groupées, auto-nettoyage configurable, totaux cumulés par compteur
- **Actualités admin** — création, édition, suppression et planification (dates début/fin)
- **Mode maintenance** — activer un message de maintenance personnalisable pour le portail
- **RGPD admin** — toggle opt-in, texte privacy éditable, suppression du cycle de vie en deux étapes

**Tâches de fond**

- **Planificateur** — tâches récurrentes avec stats de cache, déclenchement manuel, info hits/manques
- **Sauvegardes** — ZIPs manuels + tâches planifiées + procédure de restauration testée en drill, dump SQL + clé Fernet de chiffrement embarqués par défaut
- **Assistant de première configuration** — configuration guidée au premier démarrage
- **Cache image / DNS** — toggles de performance pour le proxy d'images du portail

### Portail utilisateur

Pensé pour les personnes avec qui vous partagez Emby — gamifié, social et convivial.

**Parcourir & découvrir**

- **Catalogue Découvrir** — Tendances, Populaires, Top, Oscars, Famille, À venir, par plateforme, recommandations personnalisées
- **Bandeau héro** — diaporama d'images en rotation automatique (fondu enchaîné 10 s)
- **Recherche** — suggestions TMDB instantanées avec cache 5 min, historique récent...
- **Pages détail** — sidebar premium (icônes Lucide, pastille de statut, langue & pays localisés, langue originale lue depuis TMDB)
- **Mobile-first** — grilles de jaquettes 3 colonnes sur mobile, tap-pour-ouvrir, mises en page denses, vues mobiles dédiées au besoin

**Engagement**

- **Demandes** — soumettre films, séries ou saisons ; suivi de quota, retour de statut, gestion blacklist, messages d'erreur clairs
- **Soirées ciné** — planifier des événements partagés, salle virtuelle avec mode marathon et capacité par événement (5/10/15/20), présence temps réel, vue mobile dédiée, événements passés verrouillés automatiquement après 6 h
- **Listes** — listes publiques, privées ou collaboratives avec pseudos anonymisés, liées aux familles de trophées Curateur et Bibliothécaire
- **Quoi de neuf aujourd'hui** — un overlay quotidien résumant la journée, avec le Top 3 du mois et le classement de l'utilisateur ajouté hors-podium
- **Actualités & annonces** — posts planifiés par l'admin, remontés dans la cloche

**Identité & communauté**

- **Pseudo personnalisé** — choix obligatoire à la première connexion, contrôle de disponibilité en direct, modifiable tous les 6 mois, pseudos réservés protégés
- **Avatar personnalisé** — récupère celui d'Emby ou ajoutez-en un directement sur MediaKeeper (jusqu'à 5 Mo) + titres cosmétiques avec prévisualisation avant validation
- **Paramètres premium** en cinq onglets — identité, apparence, préférences, visibilité, compte
- **Pages de profil public** — carte, bio, genres, trophées ; accessible depuis le classement
- **Série de connexions** affichée sur la page de connexion dédiée au portail

**Trophées & social**

- **160+ trophées** répartis en familles : communauté, visionnage, marathons, secrets, jalons, listes (Curateur + Bibliothécaire, 5 paliers chacun)
- **Système XP & niveaux** — progression jusqu'à 50, échelle de grades premium
- **Classement mensuel** — showcase premium : héro du champion du mois, bandeau de stats en direct, top 100, podium enrichi
- **Chat temps réel** — modération, compteur de non-lus persistant entre sessions, bouton de signalement verrouillé après envoi, messages signalés visibles par les admins et modérateurs
- **Tickets** — cibler précisément le film, la série, la saison ou l'épisode lors du signalement ; filtres par statut / source / type ; fermeture auto après 7 jours d'inactivité
- **Centre d'aide** — 15+ articles éditables par les admins avec éditeur rich-text, auto-save, brouillons, corbeille 30 jours

### Transverse

- **Interface bilingue** (français + anglais) avec parité stricte ; cascade TMDB `utilisateur → anglais → original → indépendant de la langue`
- **Container Docker unique** avec PostgreSQL 16 embarqué ; séparation web/worker possible via `MK_SEPARATE_BACKGROUND_WORKER` ; multi-arch prévu (`amd64` + `arm64`)
- **Sécurité défensive** — séparation des scopes JWT admin / portail, CSRF double-submit, login rate-limité, secrets Fernet chiffrés au repos, redaction de logs, workflow CI sécurité (`pip-audit`, `npm audit`, `bandit`, `ruff S`, `semgrep`)
- **Accessibilité complète** — focus traps sur 20+ modales, labels ARIA, navigation clavier, `prefers-reduced-motion`, toasts via `aria-live`, lien skip-to-main
- **Notifications** — cloche in-app avec messages ciblés envoyés par l'admin + webhooks Discord
- **RGPD opt-in** — export par utilisateur (JSON), texte privacy éditable par l'admin, suppression du cycle de vie en deux étapes

Pour le catalogue complet de fonctionnalités et l'historique des versions, voir le [Wiki](https://github.com/KeeperD93/mediakeeper/wiki) et les changelogs ([admin FR](backend/CHANGELOG_FR.md) · [portail FR](backend/CHANGELOG_PORTAL_FR.md)).

---

## Aperçu

### Tableau de bord admin

<!-- screenshot placeholder: tableau de bord admin (widgets, bandeau, fil d'activité) — coller ici une image 1200-1600 px de large -->

### Portail utilisateur

<!-- screenshot placeholder: accueil portail (bandeau héro, listes, jaquettes) — coller ici une image 1200-1600 px de large -->

---

## Démarrage rapide

### Démarrage express — tirer l'image publiée

La méthode la plus rapide est de tirer l'image pré-buildée depuis GitHub Container Registry. Pas de clone, pas de build :

```sh
mkdir mediakeeper && cd mediakeeper
curl -O https://raw.githubusercontent.com/KeeperD93/mediakeeper/main/docker-compose.prod.yml
docker compose -f docker-compose.prod.yml up -d
```

L'image est multi-arch (`linux/amd64` + `linux/arm64`), donc elle tourne nativement sur Synology DSM, Raspberry Pi, serveurs x86 traditionnels, etc.

**Tags d'image disponibles :**

| Tag       | Pointeur                                             | Recommandé pour                     |
| --------- | ---------------------------------------------------- | ----------------------------------- |
| `:latest` | la dernière version stable                           | self-hosters au quotidien           |
| `:beta`   | la dernière pré-release / release-candidate          | early adopters, tests               |
| `:vX.Y.Z` | une release exacte (immuable)                        | déploiements reproductibles, pin CI |
| `:X.Y`    | flottant sur la série de patch X.Y (par ex. `:0.10`) | suivre une seule branche mineure    |

### Alternative — cloner et builder depuis les sources

Pour les contributeurs ou si vous voulez l'état le plus récent de `main` :

```sh
git clone https://github.com/KeeperD93/mediakeeper.git
cd mediakeeper
docker compose up -d
```

Cette voie utilise `docker-compose.yml` (avec `build: .`) qui compile une image fraîche depuis vos sources locales.

### Premier démarrage

**Aucun `.env` requis au premier démarrage**. MediaKeeper génère automatiquement tout ce qui est sensible au boot et le persiste dans `/data/` :

- le mot de passe PostgreSQL,
- la clé JWT (≥ 32 octets),
- la clé de chiffrement Fernet pour les secrets stockés en base,
- un compte **admin** initial avec un mot de passe aléatoire imprimé une seule fois dans les logs du container.

Pour récupérer le mot de passe admin initial dès que le container est démarré :

```sh
docker compose logs mediakeeper | grep -A 6 "ADMIN ACCOUNT CREATED"
```

(Utilisez `docker compose -f docker-compose.prod.yml logs mediakeeper` à la place si vous avez démarré depuis le démarrage express GHCR.)

> [!IMPORTANT]
> Notez ce mot de passe immédiatement. Il n'est **pas** persisté sous `/data/`. En cas de raté (terminal fermé, logs rotatés), utilisez l'outil CLI de récupération — voir [`docs/operations/admin-recovery.md`](docs/operations/admin-recovery.md).

Puis ouvrez `http://<hôte>:8888`, connectez-vous avec `admin` et ce mot de passe — un changement de mot de passe est forcé à la première connexion.

**Besoin de personnaliser ?** Copiez `.env.example` en `.env` et ajustez les variables nécessaires (par ex. `TMDB_API_KEY`, `FRONTEND_ORIGIN`, `MEDIAKEEPER_PATH_ROOTS`) avant de lancer `docker compose up -d`. Les valeurs auto-générées sont conservées aux démarrages suivants.

L'application lance `alembic upgrade head` au démarrage, donc les migrations de base de données sont appliquées automatiquement.

Vous voulez mettre à jour une installation existante ? Voir [`docs/operations/updating.md`](docs/operations/updating.md).

Pour Synology DSM, les configurations reverse-proxy, le déploiement TLS et la configuration avancée, voir le [Wiki](https://github.com/KeeperD93/mediakeeper/wiki) et les runbooks d'opération dans [`docs/operations/`](docs/operations/).

---

## Documentation

| Surface                                                                        | Où                                                                                                                                                                                                                          |
| ------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Wiki utilisateur                                                               | https://github.com/KeeperD93/mediakeeper/wiki                                                                                                                                                                               |
| Runbooks d'opération (admin / sysadmin)                                        | [`docs/operations/`](docs/operations/)                                                                                                                                                                                      |
| Guides de déploiement (Caddy, Traefik, Nginx Proxy Manager, LAN, Synology DSM) | [`docs/deployment/`](docs/deployment/)                                                                                                                                                                                      |
| Contribuer                                                                     | [`CONTRIBUTING.md`](CONTRIBUTING.md)                                                                                                                                                                                        |
| Politique de sécurité                                                          | [`SECURITY.md`](SECURITY.md)                                                                                                                                                                                                |
| Code de conduite                                                               | [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)                                                                                                                                                                                  |
| Licences tierces                                                               | [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md)                                                                                                                                                                        |
| Changelog                                                                      | Admin : [`CHANGELOG_FR`](backend/CHANGELOG_FR.md) · [`CHANGELOG_EN`](backend/CHANGELOG_EN.md) · Portail : [`CHANGELOG_PORTAL_FR`](backend/CHANGELOG_PORTAL_FR.md) · [`CHANGELOG_PORTAL_EN`](backend/CHANGELOG_PORTAL_EN.md) |

---

## Communauté & support

- **Discord** — [discord.gg/A2hyNUUn6a](https://discord.gg/A2hyNUUn6a)
- **GitHub Discussions** — https://github.com/KeeperD93/mediakeeper/discussions
- **Rapports de bug & demandes de fonctionnalité** — https://github.com/KeeperD93/mediakeeper/issues
- **Signalements de sécurité** — voir [`SECURITY.md`](SECURITY.md) ; n'ouvrez **pas** d'issue publique

---

## ☕ Buy me a coffee

MediaKeeper est gratuit et open-source. Si vous l'utilisez et appréciez le travail, un café fait toujours plaisir :

- **Ko-fi** — [ko-fi.com/keeperd93](https://ko-fi.com/keeperd93) — dons ponctuels ou abonnements récurrents, PayPal et cartes acceptés
- **Mettre une étoile** — chaque étoile aide la visibilité sur GitHub

---

## Contribuer

Les pull requests sont les bienvenues. Avant de commencer, merci de lire [`CONTRIBUTING.md`](CONTRIBUTING.md) et le [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

En résumé :

1. Forker le repo et créer une branche feature (`feat/...`, `fix/...`, `refactor/...`).
2. Suivre les conventions de codage de `CONTRIBUTING.md` (i18n, mobile-first, design tokens, taille des fichiers).
3. Ajouter des tests pour tout nouvel endpoint ou composable.
4. Commiter au format [Conventional Commits](https://www.conventionalcommits.org/).
5. Ouvrir la PR ; la CI doit passer avant relecture.

---

## Développement assisté par IA

MediaKeeper est développé avec l'aide de l'IA. Chaque modification est relue, testée et committée par le mainteneur, qui reste responsable du code livré.

---

## Stack technique

| Couche              | Tech                                                                                                                      |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| **Frontend**        | Vue 3 (`<script setup>`), Vue Router 5, vue-i18n 11, Vite 6, PrimeVue 4, Chart.js 4, lucide-vue-next, TipTap              |
| **Backend**         | FastAPI (Python 3.12), SQLAlchemy 2 (async), Alembic, PyJWT, bcrypt, httpx, slowapi, cryptography (Fernet), bleach        |
| **Base de données** | PostgreSQL 16 (production, embarqué dans l'image Docker), SQLite (tests)                                                  |
| **Qualité**         | ESLint, Prettier, Stylelint, Vitest, pytest + pytest-cov, Husky + commitlint, ruff, bandit, semgrep, pip-audit, npm audit |

---

## Attribution

Ce produit utilise l'**API TMDB** mais n'est ni approuvé ni certifié par TMDB. Voir https://www.themoviedb.org pour la source de données.

MediaKeeper s'intègre avec **Emby**, **OpenSubtitles**, les webhooks **Discord** et (optionnellement) **Imgur**. Les conditions de chaque fournisseur s'appliquent lorsque ces fonctionnalités sont activées. Détails complets dans [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).

---

## Licence

MediaKeeper est publié sous **GNU General Public License v3.0 ou ultérieure** — voir [`LICENSE`](LICENSE).
