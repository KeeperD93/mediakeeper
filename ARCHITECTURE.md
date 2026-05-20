# MediaKeeper — Architecture

> Carte du code. Lecture avant première PR.
> Convention : tout nouveau mécanisme ajouté au projet est documenté ici. Pour le workflow contributeur et la check-list publique des règles de codage (mobile-first, tokens, i18n, error handling…), voir `CONTRIBUTING.md` à la racine du dépôt.
>
> Versions courantes (2026-05-14) : `APP_VERSION = 0.9.9` (admin) · `PORTAL_VERSION = 0.3.0` · `frontend/package.json = 0.9.9` · migrations Alembic livrées en continu.

---

## 1. Pile technique

| Couche | Tech |
|---|---|
| Frontend | Vue 3 `<script setup>`, Vue Router 5, vue-i18n 11, Vite 6, PrimeVue 4, Chart.js 4, lucide-vue-next, TipTap, grid-layout-plus |
| Backend | FastAPI (Python 3.12), SQLAlchemy 2 (async), Alembic, PyJWT, bcrypt, httpx, slowapi, cryptography (Fernet), bleach, pytest |
| DB | PostgreSQL 16 embarqué (prod, single container) / SQLite aiosqlite (tests) |
| Déploiement | Docker single container (PG embarqué + Uvicorn + `entrypoint.sh` qui run `alembic upgrade head` au boot, port 8888, healthcheck `/api/health?full=1`). Worker séparable via `MK_SEPARATE_BACKGROUND_WORKER=true`. |
| Qualité | ESLint 9 flat config, Prettier, stylelint, Vitest (front), pytest + pytest-cov (back), husky + commitlint (templates dans `.husky-templates/`, voir son README), CI 5 workflows (`backend.yml`, `frontend.yml`, `frontend-e2e.yml`, `commitlint.yml`, `security.yml`) |

---

## 2. Structure

```
mediakeeper/
├─ backend/                    # FastAPI app
│  ├─ main.py                  # app entrypoint — includes all routers
│  ├─ api/                     # routers (one file/folder per domain)
│  │  ├─ auth/                 # login, profile, deps, csrf, portal scope
│  │  ├─ portal/               # 30 routers : achievements, activity, admin,
│  │  │                        # availability, catalog/, chat, daily_digest,
│  │  │                        # events, featured, help, library, lists,
│  │  │                        # news, notifications, profile_settings,
│  │  │                        # profiles, requests, social, tickets, top20,
│  │  │                        # trailers, xp_events + deps.py (granular permissions)
│  │  ├─ portal_admin_*.py     # admin Portal endpoints (requests/users/feed/emby)
│  │  ├─ media/                # browse, categories, metadata, move, rename, tags, tmdb
│  │  ├─ stats/, backup/, subtitles/   # split per sub-domain
│  │  └─ <domain>.py           # changelog, healthcheck, logs, notifications,
│  │                           # onboarding, scheduler, security, settings, watchlist…
│  ├─ services/                # domain logic (not bound to HTTP)
│  │  ├─ portal/               # 80+ files : achievements (defs/checks/seed),
│  │  │                        # admin_users_*, available_*, chat, daily_digest,
│  │  │                        # discover_*, emby_index/, events (mk_events_*),
│  │  │                        # help, lists*, news, profiles, profile_stats_*,
│  │  │                        # requests*, tickets, trailers, xp, xp_boost
│  │  ├─ stats_aggregator/, stats_collector/, stats_import/
│  │  ├─ discord/, emby/, healthcheck/, opensubtitles/, media_manager/
│  │  ├─ subtitle_sources/, subtitle_tools/
│  │  ├─ scheduler/, settings/, watchlist_scanner/
│  │  └─ background_tasks.py, system.py, tmdb.py, security*.py, path_config.py
│  ├─ models/                  # SQLAlchemy models
│  │  ├─ portal/               # achievement, audit, chat, emby_tmdb_index,
│  │  │                        # event, featured, help, login_history, news,
│  │  │                        # profile, request, social, ticket, xp_boost,
│  │  │                        # xp_ledger
│  │  └─ <domain>.py           # user, user_preferences, scheduler_task, …
│  ├─ core/                    # cross-cutting (config, auth, pagination, encryption,
│  │                           # csrf_middleware, app_startup, logging)
│  ├─ alembic/versions/        # 52 migrations (applied at container boot)
│  ├─ CHANGELOG_FR.md / CHANGELOG_EN.md             # admin changelogs
│  ├─ CHANGELOG_PORTAL_FR.md / CHANGELOG_PORTAL_EN.md  # portal changelogs
│  └─ tests/                   # 47 pytest files (Tier 1 + Tier 2 + portal + phases)
├─ frontend/                   # Vue 3 SPA
│  └─ src/
│     ├─ App.vue               # root — toast container, health polling, MkConfirmDialog
│     ├─ router/               # index.js + routes/admin.js + routes/portal.js
│     ├─ views/                # top-level routed components (one per URL)
│     │  └─ portal/            # 22 portal views (PortalHome, PortalLeaderboard,
│     │                        # PortalMediaDetail, PortalSettings, CinemaRoomView, …)
│     ├─ components/           # reusable components organised by domain
│     │  ├─ common/            # MkSpinner, MkEmptyState, MkAvatar, MkConfirmDialog, TabStrip
│     │  ├─ portal/            # PortalLayout, PortalNav, MediaCard, HeroBanner,
│     │  │                     # ChatPanel, EventBanner, EventCreateModal, …
│     │  │   ├─ admin/         # AdminRequests, AdminTickets, AdminNews,
│     │  │   │                 # AdminFeatured, AdminBlacklist,
│     │  │   │                 # AdminXpEvents, AdminSettings, AdminDebug, users/
│     │  │   ├─ cinema/        # 3D-style room components
│     │  │   ├─ detail/, help/, lists/, profile/, settings/, tickets/
│     │  └─ stats/, notifications/, settings/, onboarding/, healthcheck/,
│     │     subtitles/, media-manager/, watchlist/, dashboard/, layout/
│     ├─ composables/          # use*.js — reusable logic + shared state (module-scope refs)
│     │  └─ portal/            # 30+ portal composables (useRequestStatus,
│     │                        # useProfileData, useTrophyDisplay, useMediaCardState,
│     │                        # usePortalHomeData, useTrailer, usePortalAuth, …)
│     ├─ constants/            # magic-string centralisations (toast, media, requests…)
│     ├─ locales/              # fr.json + en.json (mirrored, ~3700 lines each)
│     ├─ styles/               # design tokens + main.css entry
│     │  ├─ design-tokens.css  # imports tokens/_colors, _typography, _layout, _motion
│     │  └─ portal/            # portal namespace (--portal-*) — independent tokens
│     ├─ assets/
│     │  └─ styles/            # domain CSS files (stats, media-manager, portal/…)
│     └─ __tests__/            # 11 Vitest files (UI components + hooks + tickets)
├─ .github/                    # CI workflows + Issue/PR templates + dependabot
│  ├─ workflows/               # backend.yml, frontend.yml, frontend-e2e.yml, commitlint.yml, security.yml
│  ├─ ISSUE_TEMPLATE/          # bug_report.md, feature_request.md
│  ├─ PULL_REQUEST_TEMPLATE.md
│  └─ dependabot.yml
├─ .husky-templates/           # hooks to activate locally (pre-commit, commit-msg — see its README)
├─ README.md                   # project overview (install, deploy, links)
├─ ARCHITECTURE.md             # this file
├─ CONTRIBUTING.md             # dev setup + PR workflow + contributor checklist
├─ SECURITY.md                 # security policy & disclosure
├─ THIRD_PARTY_LICENSES.md     # third-party licences inventory
├─ commitlint.config.js        # Conventional Commits rules
├─ docker-compose.yml + Dockerfile + entrypoint.sh
└─ pytest.ini                  # backend test + coverage config
```

---

## 3. Frontend — les 4 couches

Voir aussi le rappel « Composant / Composable / `useApi` / Constantes » dans `CONTRIBUTING.md`. Résumé :

| Type | Rôle | Exemple |
|---|---|---|
| **Composant Vue** | Présente. Props, events, template, style scoped. | `MkSpinner.vue`, `HeroCarousel.vue` |
| **Composable** | Logique réutilisable + état partagé (module-scope refs). Orchestrer `useApi`. | `useWatchlist.js`, `useConfirm.js` |
| **`useApi`** | UNIQUE point de sortie HTTP. Gère JWT refresh, CSRF, 401 redirect. | `useApi.js` |
| **Constantes** | Toute string partagée (statuts, slugs, event names). | `constants/toast.js`, `constants/requests.js` |

**Pas de Pinia** — l'état partagé passe par des `ref()` au top-level d'un composable ; Vue 3 garantit qu'il est singleton par module.

---

## 4. Design system

Deux systèmes de tokens coexistent :

- **Admin** : `frontend/src/styles/tokens/_*.css` — sans préfixe (`--radius-btn`, `--surface-2`, `--duration-base`…). Utilisés par toute l'app sauf le portal.
- **Portal** : `frontend/src/styles/portal/tokens/_*.css` — préfixés `--portal-*`. Design immersif (couleurs plus saturées, shadows plus dramatiques, typography plus grande).

Règle : **aucune valeur hardcodée si un token existe** (design-tokens convention).

---

## 5. Backend — découpage

```
api/
  <domain>.py          # un router par domaine simple
  <domain>/            # router complexe découpé en sous-fichiers (auth/, portal/, media/, stats/, backup/, subtitles/)
services/
  <domain>.py          # logique métier mono-fichier
  <domain>/            # logique métier multi-fichiers organisée par sous-domaine
models/
  <domain>.py          # SQLAlchemy models, 1 fichier par table principale
  portal/              # tous les models du Portal regroupés
core/
  config.py            # Pydantic settings (env vars)
  auth.py              # JWT encode/decode, dépendances FastAPI
  csrf_middleware.py   # CSRF middleware (double-submit cookie)
  encryption.py        # Fernet symmetric encryption pour secrets en BDD
  pagination.py        # cursor-based helpers
  logging.py           # structured JSON logging
  app_startup.py       # tasks au boot (notamment encrypt_legacy_sensitive_values)
```

**`main.py`** inclut tous les routers via `app.include_router(...)`. Pas de logique métier dedans.

**Migrations Alembic** : appliquées automatiquement au boot via `entrypoint.sh` (`alembic upgrade head`). Une migration cassée = container qui ne démarre pas (fail-fast). Une migration appliquée n'est **jamais** modifiée — corriger via une nouvelle migration.

**Auth — deux scopes distincts** :
- Cookie `mk_token` (admin, scope par défaut) — accès au backoffice complet.
- Cookie `rq_token` (Portal, scope `"portal"`) — accès à `/portal/*`. `get_portal_user()` (`api/portal/deps.py`) refuse explicitement le cookie admin.
- Permissions granulaires Portal (migration 035) : `can_chat`, `can_portal`, `can_problems`, `can_lists`, `can_earn_xp_offline` — gating via `require_permission(key)`.
- Rate limiting login : 3 couches superposées — slowapi global (120/min), legacy `_rate_limit.py` deprecated (à nettoyer), DB-backed `services/security.ensure_not_blocked` (vrai mécanisme actif).

---

## 6. Data flow — un exemple concret

User clique sur "Approuver" dans `RequestsAdminView.vue` :

```
RequestsAdminView.vue         (composant : affiche + émet)
   │
   ▼
useRequestsAdmin()             (composable : orchestre)
   │  filters/sort + state partagé
   ▼
useApi.apiPost('/requests/X/approve')  (couche HTTP unique)
   │  JWT refresh, CSRF, i18n error code
   ▼
FastAPI router api/requests.py → requests_service.approve()
   │  validation, DB write, notifications service
   ▼
SQLAlchemy session, alembic-managed tables
```

Aucun composant Vue ne fait de `fetch()` direct. Aucun router FastAPI ne parle directement à la DB sans passer par un service.

---

## 7. i18n

- 2 locales : `fr` (source) + `en` (miroir).
- Toute string visible utilisateur passe par `$t('key')` ou `t('key')` (i18n convention).
- Backend renvoie des **codes d'erreur** (`invalid_credentials`, `backup_not_found`), pas des phrases. La traduction se fait côté frontend via `common.apiError.*`.

---

## 8. Changelog & versioning

Deux jeux de changelogs indépendants (admin + portal). Voir le rappel changelog dans `CONTRIBUTING.md`.

Une fois GitHub en place + Conventional Commits actifs, la génération sera semi-automatique via l'historique `feat:` / `fix:`.

---

## 9. Qualité automatique

Après `git init` + activation des hooks (`.husky-templates/README.md`), **chaque commit** passe :

1. **lint-staged** sur les fichiers staged → ESLint + Prettier + stylelint auto-fix.
2. **commitlint** → valide le format Conventional Commits.

Les tests Vitest + pytest ne s'exécutent **pas** en pre-commit (trop lents) — ils sont lancés par la CI sur push `main` et PR :
- `.github/workflows/backend.yml` — `pytest --cov --cov-report=xml` (Python 3.12, artefact 14j).
- `.github/workflows/frontend.yml` — ESLint + Stylelint + Prettier check + `vue-tsc` typecheck + Vitest + `npm run build`.
- `.github/workflows/commitlint.yml` — valide le format Conventional Commits sur PRs.
- `.github/dependabot.yml` — bumps weekly (npm + pip + github-actions, Lundi 06h00 Paris, groupes patch/minor).

**Planned for the first public release**: `release.yml` to publish multi-arch (amd64 + arm64) Docker images on `ghcr.io` and auto-create a GitHub Release from a `vX.Y.Z` tag.

---

## 10. Liens utiles

- `README.md` — vue d'ensemble produit, install, déploiement, attributions
- `CONTRIBUTING.md` — setup dev, workflow PR, check-list publique des règles de codage, ajout d'une langue
- `SECURITY.md` — politique de sécurité et procédure de signalement
- `THIRD_PARTY_LICENSES.md` — inventaire des licences open-source utilisées
- `.husky-templates/README.md` — activation des hooks
