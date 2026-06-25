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

<p align="center">
  <a href="#démarrage-rapide"><b>Démarrage</b></a> ·
  <a href="#pourquoi-mediakeeper">Pourquoi</a> ·
  <a href="#points-forts">Points forts</a> ·
  <a href="#fonctionnalités">Fonctionnalités</a> ·
  <a href="https://github.com/KeeperD93/mediakeeper/wiki">Docs</a> ·
  <a href="https://discord.gg/A2hyNUUn6a">Discord</a> ·
  <a href="https://ko-fi.com/keeperd93">Soutenir</a>
</p>

---

> [!WARNING]
> **En développement actif - pas encore stable.** MediaKeeper évolue sur la branche `v1.0.0-rc.x`, avant la première version stable `v1.0.0`. Attendez-vous à des changements et quelques bugs. Par sécurité ne l'installez pas sur vos données en production.
> Figez un tag d'image immuable (par ex. `ghcr.io/keeperd93/mediakeeper:vX.Y.Z-rc.N`) plutôt que `:latest` si vous voulez un comportement reproductible.

---

## Qu'est-ce que MediaKeeper ?

MediaKeeper se greffe à côté de votre serveur Emby et donne à deux publics leur propre surface. Les administrateurs disposent d'un back-office pour piloter la bibliothèque : doublons, santé des médias, suivi des épisodes manquants, gestion de fichiers (renommages, déplacements, création des dossiers...), sous-titres, la gestion des utilisateurs Emby, et bien plus encore. Les personnes avec qui vous partagez Emby accèdent à un portail où elles parcourent le catalogue, demandent des titres, gagnent des trophées, peuvent créer des soirées cinéma, créer des tickets, des listes de lecture, disposent d'un chat, et bien plus encore. Le tout dans un seul container Docker avec PostgreSQL embarqué, donc aucune base de données externe à brancher. Le tout disponible sur PC et mobile.

---

## Pourquoi MediaKeeper ?

La plupart des outils du domaine font une seule chose - la gestion des demandes, les statistiques, ou le nettoyage de médiathèque. MediaKeeper réunit un back-office administrateur et un portail utilisateur gamifié dans un seul container, avec quelques atouts qu'on ne trouve pas facilement ailleurs. 

| Capacité                                                            | MediaKeeper | Compagnon classique           |
| ------------------------------------------------------------------- | :---------: | :---------------------------: |
| Gamification - trophées, XP, niveaux, classement mensuel            |     ✅      |             ✗                |
| Soirées ciné partagées avec salle de cinéma virtuelle               |     ✅      |             ✗                |
| Chat temps réel, listes collaboratives, profils publics             |     ✅      |             ✗                |
| Portail de demandes social (quotas, blacklist, modération)          |     ✅      |  Souvent un simple formulaire |
| Profondeur admin - doublons, santé, watchlist, gestionnaire         |     ✅      |          Partielle            |
| Cycle de vie utilisateur - fenêtres d'accès & expiration datée      |     ✅      |          Partielle            |
| Container unique avec PostgreSQL embarqué                           |     ✅      |     Base externe courante     |
| Interface bilingue (EN + FR) avec parité stricte                    |     ✅      |           Variable            |
| Image multi-arch (amd64 + arm64)                                    |     ✅      |           Variable            |
| Outils RGPD opt-in (export par utilisateur, suppression encadrée)   |     ✅      |             ✗                |

> Comparé à la catégorie générale des compagnons média auto-hébergés, pas à un produit précis - les capacités varient selon l'outil et évoluent dans le temps.

---

## Points forts

- **Trophées & XP** : débloquez 160+ trophées répartis en de nombreuses familles, montez en niveau via un système d'XP, et grimpez au classement mensuel.
- **Soirées ciné partagées** : planifiez des événements dans une salle de cinéma virtuelle, avec mode marathon et présence temps réel.
- **Portail de demandes** : les utilisateurs demandent films, séries ou saisons ; quotas, blacklist, auto-nettoyage et modération admin sont intégrés, pas un simple formulaire.
- **Container unique** : tout tourne depuis une seule image Docker avec PostgreSQL embarqué, sans base externe à provisionner ni à sauvegarder séparément.
- **Profondeur admin** : tableau de bord live, détection de doublons, contrôles de santé de la bibliothèque, suivi des saisons manquantes et un gestionnaire de médias desktop.
- **Gestion des utilisateurs** : donnez à chaque utilisateur une fenêtre d'accès Emby qui expire à une date choisie (ou jamais), avec prolongations en un clic et désactivation automatique optionnelle des comptes échus côté Emby et MediaKeeper ; plus rôles, suppression réversible et journal d'audit.
- **Portail social** : chat temps réel modéré, listes collaboratives, profils publics, tickets et un récap quotidien.
- **Bilingue & portable** : parité stricte EN/FR de l'interface, sur une image multi-arch native amd64 et arm64 (Synology, Raspberry Pi, x86).
- **RGPD opt-in** : export des données par utilisateur, texte de confidentialité éditable par l'admin et suppression de compte en deux étapes.

---

## Aperçu

<p align="center">
  <!-- capture : tableau de bord admin (widgets, bandeau, fil d'activité) — coller ici une image 1200-1600 px de large -->
  <br>
  <em>Tableau de bord admin</em>
</p>

<p align="center">
  <!-- capture : accueil portail (bandeau héro, listes, jaquettes) — coller ici une image 1200-1600 px de large -->
  <br>
  <em>Portail utilisateur</em>
</p>

---

## Fonctionnalités

Les points forts ci-dessus sont la version courte. Voici l'étendue complète par surface - le détail fin se découvre directement dans l'application.

<details>
<summary><b>Back-office admin</b> — pour l'administrateur qui pilote l'instance Emby</summary>

<br>

- **Tableau de bord** : stats live, santé des services, fil d'activité et agencement de widgets personnalisable
- **Statistiques** : utilisateurs, bibliothèques et lectures, avec graphiques lisibles sur mobile
- **Santé des médias** : analyse de la bibliothèque regroupée par sévérité, avec jaquettes
- **Doublons** — détection à règles avec historique, liste d'ignorés et restauration
- **Suivi (watchlist)** : suivi des séries avec alertes de saisons manquantes et tags de langue audio
- **Gestionnaire de médias** (desktop) : parcourir, déplacer, renommer avec l'aide de TMDB, taguer et dédupliquer sur disque
- **Sous-titres** : téléchargement par lot OpenSubtitles, et suppression de pistes non désirées sur disque
- **Utilisateurs** : fenêtres d'accès Emby à expiration datée, rôles & permissions, quota de demandes, suppression réversible, journal d'audit et export RGPD par utilisateur
- **Demandes** : modérez les demandes avec filtres, actions groupées et auto-nettoyage configurable
- **Notifications** : envoi des notifications Discord pour plusieurs types d'informations. Plus de supports seront ajoutés par la suite.
- **Configuration** : Un panel d'outils pour gérer/configurer votre portail utilisateur pour les demandes.

</details>

<details>
<summary><b>Portail utilisateur</b> — pour les personnes avec qui vous partagez Emby</summary>

<br>

- **Découverte** : Tendances, Populaires, Mieux notés, par plateforme et recommandations personnalisées, avec recherche TMDB instantanée
- **Demandes** : soumettre films, séries ou saisons, avec suivi de quota et retour de statut clair
- **Soirées ciné** : événements partagés dans une salle virtuelle, avec mode marathon et présence temps réel
- **Listes** : publiques, privées ou collaboratives, liées aux familles de trophées Curateur et Bibliothécaire
- **Trophées & XP** : des trophées dans de nombreuses familles, un système d'XP et de niveaux, et un classement mensuel
- **Statistiques** : un accès à ses propres statistiques
- **Chat temps réel** : modéré, avec compteur de non-lus persistant et signalement des messages
- **Tickets** : signaler un problème sur un film, une série, une saison ou un épisode précis
- **Identité** : pseudo personnalisé, avatar (celui d'Emby ou votre propre upload) et titres cosmétiques
- **Profils publics**, un **récap quotidien**, des **actualités in-app** et un **centre d'aide** éditable par l'admin

</details>

<details>
<summary><b>Transverse</b> : plateforme, sécurité, accessibilité et i18n</summary>

<br>

- **Interface bilingue** (anglais + français) avec parité stricte des locales
- **Container Docker unique** avec PostgreSQL embarqué ; un worker séparé optionnel pour la production ; multi-arch (amd64 + arm64)
- **Sécurité défensive** : sessions admin/portail séparées, protection CSRF, login rate-limité, secrets chiffrés au repos, redaction des logs et un pipeline CI de sécurité
- **Accessibilité** : focus traps, labels ARIA, navigation clavier, support du reduced-motion et lien skip-to-main
- **Notifications** : une cloche in-app avec messages poussés par l'admin, plus des webhooks Discord
- **RGPD opt-in** : export par utilisateur, texte de confidentialité éditable par l'admin et suppression en deux étapes

</details>

Pour le catalogue complet de fonctionnalités et l'historique des versions, voir le [Wiki](https://github.com/KeeperD93/mediakeeper/wiki) et les changelogs ([admin FR](backend/CHANGELOG_FR.md) · [portail FR](backend/CHANGELOG_PORTAL_FR.md)).

---

## Démarrage rapide

### Démarrage express - tirer l'image publiée

La méthode la plus rapide est d'installer l'image pré-buildée depuis GitHub Container Registry. Pas de clone, pas de build :

```sh
mkdir mediakeeper && cd mediakeeper
curl -O https://raw.githubusercontent.com/KeeperD93/mediakeeper/main/docker-compose.prod.yml
docker compose -f docker-compose.prod.yml up -d
```

L'image est multi-arch (`linux/amd64` + `linux/arm64`), donc elle tourne nativement sur Synology DSM, Raspberry Pi, serveurs x86 traditionnels, etc.

<details>
<summary>Tags d'image et build depuis les sources</summary>

<br>

**Tags d'image disponibles :**

| Tag       | Pointeur                                             | Recommandé pour                     |
| --------- | ---------------------------------------------------- | ----------------------------------- |
| `:latest` | la dernière version stable                           | self-hosters au quotidien           |
| `:beta`   | la dernière pré-release / release-candidate          | early adopters, tests               |
| `:vX.Y.Z` | une release exacte (immuable)                        | déploiements reproductibles, pin CI |
| `:X.Y`    | flottant sur la série de patch X.Y (par ex. `:1.0`)  | suivre une seule branche mineure    |

### Alternative — cloner et builder depuis les sources

Pour les contributeurs ou si vous voulez l'état le plus récent de `main` :

```sh
git clone https://github.com/KeeperD93/mediakeeper.git
cd mediakeeper
docker compose up -d
```

Cette voie utilise `docker-compose.yml` (avec `build: .`) qui compile une image fraîche depuis vos sources locales.

</details>

### Premier démarrage

**Aucun `.env` requis au premier démarrage**. MediaKeeper génère automatiquement tout ce qui est sensible au boot et le persiste dans `/data/` :

- le mot de passe PostgreSQL,
- la clé JWT,
- la clé de chiffrement des secrets stockés en base,
- un compte **admin** initial avec un mot de passe aléatoire imprimé une seule fois dans les logs du container.

Pour récupérer le mot de passe admin initial dès que le container est démarré :

```sh
docker compose logs mediakeeper | grep -A 6 "ADMIN ACCOUNT CREATED"
```

(Utilisez `docker compose -f docker-compose.prod.yml logs mediakeeper` à la place si vous avez démarré depuis le démarrage express GHCR.)

> [!IMPORTANT]
> Notez ce mot de passe immédiatement. Il n'est **pas** persisté sous `/data/`. En cas de raté (terminal fermé, logs rotatés), utilisez l'outil CLI de récupération — voir [`docs/operations/admin-recovery.md`](docs/operations/admin-recovery.md).

Puis ouvrez `http://<hôte>:8888`, connectez-vous avec `admin` et ce mot de passe - un changement de mot de passe est forcé à la première connexion.

**Besoin de personnaliser ?** Copiez `.env.example` en `.env` et ajustez les variables nécessaires (par ex. `TMDB_API_KEY`, `FRONTEND_ORIGIN`, `MEDIAKEEPER_PATH_ROOTS`) avant de lancer `docker compose up -d`. Les valeurs auto-générées sont conservées aux démarrages suivants.

L'application applique automatiquement les migrations de base de données au démarrage.

Vous voulez mettre à jour une installation existante ? Voir [`docs/operations/updating.md`](docs/operations/updating.md).

Pour Synology DSM, les configurations reverse-proxy, le déploiement TLS et la configuration avancée, voir le [Wiki](https://github.com/KeeperD93/mediakeeper/wiki) et les runbooks d'opération dans [`docs/operations/`](docs/operations/).

---

## Documentation

| Surface                                                                        | Où                                                                                                                                                                                                                          |
| ------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Wiki utilisateur                                                               | https://github.com/KeeperD93/mediakeeper/wiki                                                                                                                                                                               |
| Runbooks d'opération (admin / sysadmin)                                        | [`docs/operations/`](docs/operations/)                                                                                                                                                                                      |
| Guides de déploiement (Caddy, Traefik, Nginx Proxy Manager, LAN, Synology DSM) | [`docs/deployment/`](docs/deployment/)                                                                                                                                                                                      |
| Contribuer                                                                     | [`CONTRIBUTING-fr.md`](CONTRIBUTING-fr.md)                                                                                                                                                                                  |
| Politique de sécurité                                                          | [`SECURITY-fr.md`](SECURITY-fr.md)                                                                                                                                                                                          |
| Code de conduite                                                               | [`CODE_OF_CONDUCT-fr.md`](CODE_OF_CONDUCT-fr.md)                                                                                                                                                                            |
| Licences tierces                                                               | [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md)                                                                                                                                                                        |
| Changelog                                                                      | Admin : [`CHANGELOG_FR`](backend/CHANGELOG_FR.md) · [`CHANGELOG_EN`](backend/CHANGELOG_EN.md) · Portail : [`CHANGELOG_PORTAL_FR`](backend/CHANGELOG_PORTAL_FR.md) · [`CHANGELOG_PORTAL_EN`](backend/CHANGELOG_PORTAL_EN.md) |

---

## Communauté & support

- **Discord** : [discord.gg/A2hyNUUn6a](https://discord.gg/A2hyNUUn6a)
- **GitHub Discussions** : https://github.com/KeeperD93/mediakeeper/discussions
- **Feuille de route** : tableau public de ce qui est prévu : https://github.com/users/KeeperD93/projects/1
- **Rapports de bug & demandes de fonctionnalité** : https://github.com/KeeperD93/mediakeeper/issues
- **Signalements de sécurité** : voir [`SECURITY-fr.md`](SECURITY-fr.md) ; n'ouvrez **pas** d'issue publique

---

## ☕ Offrez-moi un café

MediaKeeper est gratuit et open-source. Si vous l'utilisez et appréciez le travail, un café fait toujours plaisir :

- **Ko-fi** : [ko-fi.com/keeperd93](https://ko-fi.com/keeperd93) - dons ponctuels ou abonnements récurrents, PayPal et cartes acceptés
- **Mettre une étoile** : chaque étoile aide la visibilité sur GitHub

---

## Contribuer

Les pull requests sont les bienvenues. Avant de commencer, merci de lire [`CONTRIBUTING-fr.md`](CONTRIBUTING-fr.md) et le [`CODE_OF_CONDUCT-fr.md`](CODE_OF_CONDUCT-fr.md).

En résumé :

1. Forker le repo et créer une branche feature (`feat/...`, `fix/...`, `refactor/...`).
2. Suivre les conventions de codage de `CONTRIBUTING-fr.md` (i18n, mobile-first, design tokens, taille des fichiers).
3. Ajouter des tests pour tout nouvel endpoint ou composable.
4. Commiter au format [Conventional Commits](https://www.conventionalcommits.org/).
5. Ouvrir la PR ; la CI doit passer avant relecture.

---

## Développement assisté par IA

MediaKeeper est développé avec l'aide de l'IA. Chaque modification est relue, testée et committée par le mainteneur.

---

## Stack technique

<details>
<summary>Frontend, backend, base de données et outils qualité</summary>

<br>

| Couche              | Tech                                                                                                |
| ------------------- | --------------------------------------------------------------------------------------------------- |
| **Frontend**        | Vue, Vue Router, vue-i18n, Vite, PrimeVue, Chart.js, lucide-vue-next, TipTap                        |
| **Backend**         | FastAPI (Python), SQLAlchemy (async), Alembic, PyJWT, bcrypt, httpx, slowapi, cryptography, bleach  |
| **Base de données** | PostgreSQL (embarqué dans l'image), SQLite (tests)                                                  |
| **Qualité**         | ESLint, Prettier, Stylelint, Vitest, pytest, Husky + commitlint, ruff, bandit, semgrep, pip-audit, npm audit |

</details>

---

## Attribution

Ce produit utilise l'**API TMDB** mais n'est ni approuvé ni certifié par TMDB. Voir https://www.themoviedb.org pour la source de données.

MediaKeeper s'intègre avec **Emby**, **OpenSubtitles**, les webhooks **Discord** et (optionnellement) **Imgur**. Les conditions de chaque fournisseur s'appliquent lorsque ces fonctionnalités sont activées. Détails complets dans [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).

---

## Licence

MediaKeeper est publié sous **GNU General Public License v3.0 ou ultérieure** — voir [`LICENSE`](LICENSE).
