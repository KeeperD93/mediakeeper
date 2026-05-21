# Contribuer à MediaKeeper

<p align="center">
  <a href="CONTRIBUTING.md">English</a> · <b>Français</b>
</p>

Merci de votre intérêt pour contribuer au projet. Ce fichier décrit le **workflow** (setup dev, structure du projet, lint, tests, commits, PRs) et les **conventions de codage** que chaque contributeur suit.

Avant toute chose, merci de lire le [Code de conduite](CODE_OF_CONDUCT-fr.md) et la [Politique de sécurité](SECURITY-fr.md).

---

## Prérequis

- **Node.js** ≥ 20 et **npm** ≥ 10 (frontend)
- **Python** ≥ 3.11 (backend — uniquement si vous l'exécutez localement, sinon Docker suffit)
- **Docker** + **docker compose** (recommandé pour un backend en mode production-like)
- **Git**

---

## Configuration initiale

```sh
git clone https://github.com/KeeperD93/mediakeeper.git
cd mediakeeper

# Frontend
cd frontend
npm install
cp .env.example .env
npm run dev            # http://localhost:5173

# Backend (en local, sans Docker)
cd ../backend
pip install -r requirements.txt
uvicorn main:app --reload

# OU backend dans Docker
cd ..
docker compose up -d
```

Activez les hooks de commit (Husky + commitlint) :

```sh
cd <repo-root>
mkdir -p .husky
cp .husky-templates/pre-commit .husky/pre-commit
cp .husky-templates/commit-msg .husky/commit-msg
chmod +x .husky/*
git config core.hooksPath .husky
```

---

## Structure du projet

Vue d'ensemble courte et haut niveau. Le code lui-même fait foi.

```
mediakeeper/
├── backend/                   # Application FastAPI
│   ├── main.py                # Entrypoint ASGI, inclut chaque router
│   ├── api/                   # Routers HTTP (un dossier/fichier par domaine)
│   ├── services/              # Logique métier ; les routers restent fins et ne touchent jamais la DB directement
│   ├── models/                # Modèles SQLAlchemy 2 (un fichier par table, modèles portail sous `portal/`)
│   ├── core/                  # Transverse : sécurité, CSRF, chiffrement, pagination, logging, helpers async
│   ├── alembic/versions/      # Migrations DB, appliquées au boot du container
│   ├── CHANGELOG_FR.md        # Changelog admin user-facing (source FR)
│   ├── CHANGELOG_EN.md        # Changelog admin user-facing (miroir EN)
│   ├── CHANGELOG_PORTAL_FR.md # Changelog portail viewer (source FR)
│   ├── CHANGELOG_PORTAL_EN.md # Changelog portail viewer (miroir EN)
│   └── tests/                 # Suites pytest
├── frontend/                  # SPA Vue 3
│   └── src/
│       ├── components/        # Composants Vue présentationnels (admin + namespace portal/)
│       ├── composables/       # Logique réutilisable + état partagé module-scope (use*.js)
│       ├── views/             # Pages au niveau routeur
│       ├── router/            # Configuration vue-router
│       ├── locales/           # fr.json (source) + en.json (miroir)
│       ├── styles/            # Design tokens + main stylesheet
│       ├── assets/styles/     # Fichiers CSS par domaine
│       ├── constants/         # Magic strings partagés (statuts, slugs, noms d'événements)
│       └── utils/             # Utilitaires purs
├── docs/                      # Runbooks d'opération et de déploiement
├── .github/                   # Workflows CI + templates Issue/PR + config Dependabot
├── .husky-templates/          # Hooks à activer localement (pre-commit, commit-msg)
└── docker-compose.yml + Dockerfile + entrypoint.sh
```

Le projet est un **monolithe assumé**. Deux surfaces (admin + portail) vivent dans la même app FastAPI et la même SPA Vue, mais utilisent des cookies JWT distincts (`mk_token` pour admin, `rq_token` pour portail) et des arbres de routes distincts.

---

## Conventions de codage

Ces règles que chaque PR doit suivre. Elles s'appliquent aussi bien aux features, fixes et refactors.

### Frontend

- **i18n** — chaque chaîne user-facing passe par `$t('clé')` / `t('clé')`. Ne jamais hardcoder de texte français ou anglais dans les templates ou scripts. Ajoutez la clé **dans les deux** `frontend/src/locales/fr.json` et `frontend/src/locales/en.json` (FR est la source, EN est le miroir).
- **Mobile-first** — les styles par défaut ciblent le plus petit viewport ; élargir via `@media (min-width: ...)`. Utilisez uniquement les breakpoints du projet dans `frontend/src/styles/breakpoints.css`. Touch targets ≥ 44 × 44 px sur mobile. Les effets `:hover` doivent être wrappés dans `@media (hover: hover) { … }`.
- **Sûreté overflow** — les racines de page utilisent `overflow-x: clip` (pas `hidden`) pour qu'un descendant large ne déclenche pas l'auto-zoom-out mobile et que le document continue à scroller verticalement.
- **Design tokens** — ne jamais hardcoder une couleur, un radius, une font-size, une ombre ou un espacement si un token existe. Préférez le token du projet (par ex. `var(--accent-500)`, `var(--radius-btn)`) à une valeur littérale.
- **Pas de style inline** — les attributs `style="..."` ne sont pas autorisés dans les templates sauf pour les valeurs réellement calculées au runtime. Déplacez les règles présentationnelles dans un bloc `<style scoped>` ou un fichier CSS sous `assets/styles/`.
- **Pattern à quatre couches** — répartissez le travail entre :
  - **Composant** (Vue SFC) — présentation, props, events, style scoped
  - **Composable** (`use*.js`) — logique réutilisable + état partagé
  - **`useApi`** — l'unique frontière HTTP (gère refresh JWT, CSRF, redirection 401). Ne jamais appeler `fetch()` directement depuis un composant.
  - **Constantes** (`frontend/src/constants/*.js`) — chaque chaîne partagée (statut, slug, nom d'événement)
- **Vue scoped CSS** — quand vous extrayez des styles d'un composant vers `assets/styles/...`, préfixez chaque sélecteur avec la classe racine du composant (par ex. `.pt-help-…`) pour simuler le scoping. Valeurs uniquement par tokens.
- **Icônes** — source unique `lucide-vue-next` ; pas de `<svg>` inline ni de `<path>` à la main pour une icône déjà exposée par Lucide.

### Backend

- Un router = un domaine. La logique métier vit dans un service ; un router ne parle jamais directement à la base de données.
- Migration DB → un nouveau fichier Alembic. **Ne pas** modifier une migration existante une fois qu'elle a été appliquée.
- Les erreurs remontées à l'utilisateur sont des **codes i18n** (par ex. `errors.embyUnreachable`), pas des phrases complètes ; le frontend les traduit.
- Levez `HTTPException` pour les chemins d'erreur. **Ne pas** retourner `200 OK + {"error": "..."}` depuis un router — ça casse l'observabilité et la vérif `!res.ok` côté frontend.
- Utilisez le helper `core/async_utils.safe_create_task` pour les tâches d'arrière-plan fire-and-forget au lieu d'un `asyncio.create_task` brut — il logue les exceptions non gérées au lieu de les avaler.

### Transverse

- **Taille des fichiers** — chaque fichier applicatif (Vue, JS/TS, Python, CSS, tests inclus) vise **300 lignes ou moins** comme limite souple. Un fichier peut légitimement atteindre **jusqu'à 400 lignes** quand il couvre un widget fortement couplé ou un scénario de test qui ne peut pas être splitté proprement — signalez l'exception explicitement dans la description de la PR. **500 lignes est le plafond dur** : au-delà, le fichier doit être splitté avant d'ajouter toute nouvelle feature.
- **Langue du code** — les commentaires, docstrings, messages de log, identifiants sont écrits en anglais. Les locales `*.fr.json` et les fichiers `CHANGELOG_FR.md` sont les seules surfaces françaises par design.
- **Dates / fuseaux horaires** — stockez en UTC avec timezone, transmettez en ISO 8601, formatez côté frontend avec `Intl.DateTimeFormat` et la locale utilisateur. Ne jamais hardcoder un fuseau horaire ou `'fr-FR'`.

---

## Workflow de développement

### 1. Branche de travail

```sh
git checkout -b feat/ma-feature   # ou fix/..., refactor/..., docs/..., chore/...
```

Préfixes recommandés : `feat/`, `fix/`, `refactor/`, `docs/`, `chore/`, `perf/`.

### 2. Code

Utilisez les composants frontend partagés (`MkSpinner`, `MkEmptyState`, `MkAvatar`, `MkConfirmDialog`) et les classes utilitaires (`mk-modal-sheet`, `pt-carousel-arrow`, `pt-edge-fade`) avant d'en introduire de nouveaux. Pour les services backend, suivez le découpage router-fin / service-épais.

### 3. Lint et format

```sh
cd frontend
npm run lint              # ESLint
npm run stylelint         # stylelint
npm run format            # Prettier
npm run typecheck         # vue-tsc
```

Une fois les hooks Husky actifs (voir *Configuration initiale*), `git commit` déclenche automatiquement `lint-staged` sur les fichiers stagés.

### 4. Tests

```sh
# Tests unitaires frontend
cd frontend
npm run test:unit               # passe unique
npm run test:unit:watch         # mode watch
npm run test:coverage           # + rapport de couverture

# Tests backend
cd backend
pytest                          # suite complète
pytest --cov                    # + couverture
pytest tests/test_auth_login.py -v   # fichier spécifique
```

**Tout nouvel endpoint API doit avoir au moins un test.**

### 5. Commit

Format [Conventional Commits](https://www.conventionalcommits.org/) :

```
<type>(<scope>): <sujet>

[corps optionnel]

[footer optionnel]
```

Types autorisés : `feat`, `fix`, `refactor`, `perf`, `docs`, `style`, `test`, `build`, `ci`, `chore`, `revert`.

Exemples :

```
feat(portal): add trophy unlock toast
fix(media-manager): handle empty filename in rename batch
refactor(stats): extract StatsUserPopover into composable
chore(deps): bump vite to 6.4.2
```

Longueur max du header : 120 caractères.

### 6. Changelog user-facing

Si le changement est **visible par l'utilisateur final** (feature, fix UX, nouvelle option), ajoutez une entrée `[Unreleased]` dans le changelog concerné (admin ou portail, FR + EN miroir). Les entrées sont courtes (≤ 12 mots), décrivent le changement en termes produit, ne nomment jamais un produit externe ni de « source d'inspiration ».

Le projet maintient **deux paires de changelogs** :

- Admin / back-office : `backend/CHANGELOG_FR.md` ↔ `backend/CHANGELOG_EN.md` (versionné via `APP_VERSION`).
- Portail viewer : `backend/CHANGELOG_PORTAL_FR.md` ↔ `backend/CHANGELOG_PORTAL_EN.md` (versionné via `PORTAL_VERSION`).

Un changement qui touche les deux surfaces est loggé dans les deux paires. **Ne pas ajouter** d'entrée pour : refactors, renommages internes, migrations techniques, tests, docs.

### 7. Pull request

```sh
git push origin feat/ma-feature
# puis ouvrir une PR sur GitHub
```

Dans la description de la PR :

- **Ce que ça fait** (1–2 phrases)
- **Pourquoi** (contexte métier si applicable)
- **Comment tester** (étapes reproductibles)
- **Captures d'écran** si changements UI
- **Breaking changes** s'il y en a

La CI lance lint + tests sur chaque PR (`backend.yml`, `frontend.yml`, `frontend-e2e.yml`, `commitlint.yml`, `security.yml`). Chaque PR doit passer avant relecture.

---

## Ajouter une langue (i18n)

Le projet livre actuellement **2 locales** : `fr.json` (source) et `en.json` (miroir). Pour ajouter une nouvelle langue :

1. Copiez `frontend/src/locales/en.json` vers `frontend/src/locales/<code>.json` (par ex. `de.json`, `es.json`).
2. Traduisez **toutes les valeurs** sans toucher aux clés.
3. Enregistrez le code dans `frontend/src/i18n.js` (locales chargées + nom natif affiché dans le sélecteur).
4. Lancez `node frontend/scripts/check-integrity.mjs` et vérifiez qu'il ne signale aucune clé manquante.
5. Ouvrez une PR titrée `feat(i18n): add <langue> locale`.

Les contributions de traduction sont les bienvenues.

---

## Ajouter une dépendance

**Frontend :**

```sh
cd frontend
npm install --save <pkg>        # dépendance runtime
npm install --save-dev <pkg>    # dépendance dev
```

**Backend :** éditez `backend/requirements.txt` manuellement (pin de la version), puis rebuild le container ou `pip install -r requirements.txt`.

Avant d'ajouter une dépendance :

1. Vérifiez qu'aucune solution native ou déjà installée ne couvre le besoin.
2. Vérifiez l'impact sur le bundle frontend (`npm run build`) pour les deps frontend.
3. Vérifiez la compatibilité de licence (MIT / Apache 2 / BSD OK — GPL / AGPL nécessite justification, voir [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md)).
4. Vérifiez la santé upstream (releases récentes, statut de maintenance, issues ouvertes).

---

## Secrets

- **Ne jamais** commiter de secrets (clés API, mots de passe, tokens). Utilisez des variables d'environnement.
- `.env` est gitignored. `.env.example` documente chaque variable lue par le backend.
- Si un secret fuite, révoquez-le **immédiatement** chez le fournisseur, puis purgez-le de l'historique Git.

---

## Mettre à jour ce fichier

Quand une convention de workflow change (nouveau hook activé, nouveau test runner, règle de codage qui évolue…), mettez à jour ce fichier **dans le même commit**. Une doc périmée n'aide personne.

---

## Questions

- **Rapports de bug & demandes de fonctionnalité** — ouvrir une issue GitHub via les templates dans `.github/ISSUE_TEMPLATE/`.
- **Discussions, aide, idées** — utiliser [GitHub Discussions](https://github.com/KeeperD93/mediakeeper/discussions) ou le Discord du projet (lien dans le [README](README-fr.md)).
- **Signalements de sécurité** — voir [`SECURITY-fr.md`](SECURITY-fr.md).
