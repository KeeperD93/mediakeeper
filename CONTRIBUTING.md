# Contributing to MediaKeeper

<p align="center">
  <b>English</b> · <a href="CONTRIBUTING-fr.md">Français</a>
</p>

Thanks for considering a contribution. This file describes the **workflow** (dev setup, project structure, lint, tests, commits, PRs) and the **coding conventions** every contributor follows.

Before anything else, please read the [Code of Conduct](CODE_OF_CONDUCT.md) and the [Security policy](SECURITY.md).

---

## Prerequisites

- **Node.js** ≥ 22.12 and **npm** ≥ 10 (frontend)
- **Python** ≥ 3.11 (backend — only when running it locally, otherwise Docker is enough)
- **Docker** + **docker compose** (recommended for a production-like backend)
- **Git**

---

## Initial setup

```sh
git clone https://github.com/KeeperD93/mediakeeper.git
cd mediakeeper

# Frontend
cd frontend
npm install
cp .env.example .env
npm run dev            # http://localhost:5173

# Backend (locally, no Docker)
cd ../backend
pip install -r requirements.txt
uvicorn main:app --reload

# OR backend in Docker
cd ..
docker compose up -d
```

Activate the commit hooks (Husky + commitlint):

```sh
cd <repo-root>
mkdir -p .husky
cp .husky-templates/pre-commit .husky/pre-commit
cp .husky-templates/commit-msg .husky/commit-msg
chmod +x .husky/*
git config core.hooksPath .husky
```

---

## Project structure

A short, high-level overview. The code itself is the source of truth.

```
mediakeeper/
├── backend/                   # FastAPI app
│   ├── main.py                # ASGI entrypoint, includes every router
│   ├── api/                   # HTTP routers (one folder/file per domain)
│   ├── services/              # business logic; routers stay thin and never touch the DB directly
│   ├── models/                # SQLAlchemy 2 models (one file per table, portal models under `portal/`)
│   ├── core/                  # cross-cutting: security, CSRF, encryption, pagination, logging, async helpers
│   ├── alembic/versions/      # DB migrations, applied at container boot
│   ├── CHANGELOG_FR.md        # admin user-facing changelog (FR source)
│   ├── CHANGELOG_EN.md        # admin user-facing changelog (EN mirror)
│   ├── CHANGELOG_PORTAL_FR.md # portal viewer changelog (FR source)
│   ├── CHANGELOG_PORTAL_EN.md # portal viewer changelog (EN mirror)
│   └── tests/                 # pytest suites
├── frontend/                  # Vue 3 SPA
│   └── src/
│       ├── components/        # presentational Vue SFCs (admin + portal/ namespace)
│       ├── composables/       # reusable logic + module-scope shared state (use*.js)
│       ├── views/             # router-level pages
│       ├── router/            # vue-router config
│       ├── locales/           # fr.json (source) + en.json (mirror)
│       ├── styles/            # design tokens + main stylesheet
│       ├── assets/styles/     # CSS files per domain
│       ├── constants/         # shared magic strings (status, slugs, event names)
│       └── utils/             # pure utilities
├── docs/                      # operations and deployment runbooks
├── .github/                   # CI workflows + Issue/PR templates + Dependabot config
├── .husky-templates/          # hooks to activate locally (pre-commit, commit-msg)
└── docker-compose.yml + Dockerfile + entrypoint.sh
```

The project is a **monolith on purpose**. Two surfaces (admin + portal) live in the same FastAPI app and the same Vue SPA, but use distinct JWT cookies (`mk_token` for admin, `rq_token` for portal) and distinct route trees.

---

## Coding conventions

These are the rules every PR must follow. They apply equally to features, fixes and refactors.

### Frontend

- **i18n** — every user-facing string goes through `$t('key')` / `t('key')`. Never hardcode French or English text in templates or scripts. Add the key to **both** `frontend/src/locales/fr.json` and `frontend/src/locales/en.json` (FR is the source, EN is the mirror).
- **Mobile-first** — default styles target the smallest viewport; widen via `@media (min-width: ...)`. Only use the project breakpoints from `frontend/src/styles/breakpoints.css`. Touch targets ≥ 44 × 44 px on mobile. `:hover` effects must be wrapped in `@media (hover: hover) { … }`.
- **Overflow safety** — page roots use `overflow-x: clip` (not `hidden`) so a wide descendant cannot trigger mobile auto-zoom-out and the document keeps scrolling vertically.
- **Design tokens** — never hardcode a colour, radius, font size, shadow or spacing if a token exists. Prefer the project token (e.g. `var(--accent-500)`, `var(--radius-btn)`) over a literal value.
- **No inline styles** — `style="..."` attributes are not allowed in templates except for genuinely runtime-computed values. Move presentational rules into a `<style scoped>` block or a CSS file under `assets/styles/`.
- **Four-layer pattern** — split work between:
  - **Component** (Vue SFC) — presentation, props, events, scoped style
  - **Composable** (`use*.js`) — reusable logic + shared state
  - **`useApi`** — the only HTTP boundary (handles JWT refresh, CSRF, 401 redirect). Never call `fetch()` directly from a component.
  - **Constants** (`frontend/src/constants/*.js`) — every shared string (status, slug, event name)
- **Vue scoped CSS** — when extracting styles from a component into `assets/styles/...`, prefix every selector with the component's root class (e.g. `.pt-help-…`) to simulate scoping. Tokens-only values.
- **Icons** — single source `lucide-vue-next`; no inline `<svg>` or hand-drawn `<path>` for an icon already exposed by Lucide.

### Backend

- One router = one domain. Business logic lives in a service; a router never talks directly to the database.
- DB migration → a new Alembic file. Do **not** modify an existing migration once it has been applied.
- Errors surfaced to the user are **i18n codes** (e.g. `errors.embyUnreachable`), not full sentences; the frontend translates them.
- Raise `HTTPException` for error paths. Do **not** return `200 OK + {"error": "..."}` from a router — it breaks observability and the frontend's `!res.ok` check.
- Use the `core/async_utils.safe_create_task` helper for fire-and-forget background tasks instead of raw `asyncio.create_task` — it logs unhandled exceptions instead of swallowing them.

### Cross-cutting

- **File size** — every applicative file (Vue, JS/TS, Python, CSS, tests included) targets **300 lines or less** as the soft limit. A file may legitimately reach **up to 400 lines** when it covers a tightly coupled widget or test scenario that cannot be split cleanly — flag the exception explicitly in the PR description. **500 lines is the hard ceiling**: beyond that, the file must be split before adding any new feature.
- **Code language** — comments, docstrings, log messages, identifiers are written in English. The `*.fr.json` locales and the `CHANGELOG_FR.md` files are the only French-by-design surfaces.
- **Dates / timezones** — store UTC with timezone, transmit ISO 8601, format on the frontend with `Intl.DateTimeFormat` and the user locale. Never hardcode a timezone or `'fr-FR'`.

---

## Development workflow

### 1. Working branch

```sh
git checkout -b feat/my-feature   # or fix/..., refactor/..., docs/..., chore/...
```

Recommended prefixes: `feat/`, `fix/`, `refactor/`, `docs/`, `chore/`, `perf/`.

### 2. Code

Use the shared frontend components (`MkSpinner`, `MkEmptyState`, `MkAvatar`, `MkConfirmDialog`) and utility classes (`mk-modal-sheet`, `pt-carousel-arrow`, `pt-edge-fade`) before introducing new ones. For backend services, follow the router-thin / service-thick split.

### 3. Lint and format

```sh
cd frontend
npm run lint              # ESLint
npm run stylelint         # stylelint
npm run format            # Prettier
npm run typecheck         # vue-tsc
```

Once Husky hooks are active (see _Initial setup_), `git commit` triggers `lint-staged` automatically on staged files.

### 4. Tests

```sh
# Frontend unit tests
cd frontend
npm run test:unit               # single pass
npm run test:unit:watch         # watch mode
npm run test:coverage           # + coverage report

# Backend tests
cd backend
pytest                          # full suite
pytest --cov                    # + coverage
pytest tests/test_auth_login.py -v   # specific file
```

**Every new API endpoint must have at least one test.**

### 5. Commit

[Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

Allowed types: `feat`, `fix`, `refactor`, `perf`, `docs`, `style`, `test`, `build`, `ci`, `chore`, `revert`.

Examples:

```
feat(portal): add trophy unlock toast
fix(media-manager): handle empty filename in rename batch
refactor(stats): extract StatsUserPopover into composable
chore(deps): bump vite to 6.4.2
```

Header max length: 120 characters.

### 6. User-facing changelog

If the change is **visible to end users** (feature, UX fix, new option), add an `[Unreleased]` entry in the relevant changelog (admin or portal, FR + EN mirrored). Entries are short (≤ 12 words), describe the change in product terms, never name an external product or "inspiration source".

The project ships **two changelog pairs**:

- Admin / back-office: `backend/CHANGELOG_FR.md` ↔ `backend/CHANGELOG_EN.md` (versioned via `APP_VERSION`).
- Portal viewer: `backend/CHANGELOG_PORTAL_FR.md` ↔ `backend/CHANGELOG_PORTAL_EN.md` (versioned via `PORTAL_VERSION`).

A change touching both surfaces is logged in both pairs. **Do not add** an entry for: refactors, internal renames, technical migrations, tests, docs.

### 7. Pull request

```sh
git push origin feat/my-feature
# then open a PR on GitHub
```

In the PR description:

- **What it does** (1–2 sentences)
- **Why** (business context if applicable)
- **How to test** (reproducible steps)
- **Screenshots** if UI changes
- **Breaking changes** if any

CI runs lint + tests on every PR (`backend.yml`, `frontend.yml`, `frontend-e2e.yml`, `commitlint.yml`, `security.yml`). Every PR must pass before review.

---

## Adding a language (i18n)

The project currently ships **2 locales**: `fr.json` (source) and `en.json` (mirror). To add a new language:

1. Copy `frontend/src/locales/en.json` to `frontend/src/locales/<code>.json` (e.g. `de.json`, `es.json`).
2. Translate **all values** without touching the keys.
3. Register the code in `frontend/src/i18n.js` (loaded locales + native name shown in the picker).
4. Run `node frontend/scripts/check-integrity.mjs` and make sure it reports no missing keys.
5. Open a PR titled `feat(i18n): add <language> locale`.

Translation contributions are welcome.

---

## Adding a dependency

**Frontend:**

```sh
cd frontend
npm install --save <pkg>        # runtime dependency
npm install --save-dev <pkg>    # dev dependency
```

**Backend:** edit `backend/requirements.txt` manually (pin the version), then rebuild the container or `pip install -r requirements.txt`.

Before adding any dependency:

1. Check that no native or already-installed solution covers the need.
2. Check the frontend bundle impact (`npm run build`) for frontend dependencies.
3. Check the licence is compatible (MIT / Apache 2 / BSD OK — GPL / AGPL needs justification, see [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md)).
4. Check upstream health (recent releases, maintenance status, open issues).

---

## Release process

Releases are tagged from `main` via the CLI; the maintainer is the only person who triggers them. Contributors only need to know that their merged PRs accumulate in the `[Unreleased]` sections of the four changelogs (`backend/CHANGELOG_{EN,FR}.md`, `backend/CHANGELOG_PORTAL_{EN,FR}.md`) and will ship in the next tagged release.

### How a release is cut

1. A `chore(release): prepare vX.Y.Z` PR freezes the `[Unreleased]` sections into a dated `[X.Y.Z]` block in the four changelogs, and bumps the three version markers:
   - `APP_VERSION` in [`backend/api/changelog.py`](backend/api/changelog.py)
   - `PORTAL_VERSION` in [`backend/api/portal_changelog.py`](backend/api/portal_changelog.py)
   - `version` in [`frontend/package.json`](frontend/package.json)
2. Once that PR is merged, the maintainer pushes a `v*` tag locally (`git tag vX.Y.Z && git push --tags`).
3. The [`.github/workflows/release.yml`](.github/workflows/release.yml) workflow builds a multi-arch image (`linux/amd64` + `linux/arm64`), pushes it to GHCR, and creates the matching GitHub Release with a body extracted from the EN changelogs.

### Channels and GHCR tags

| Tag pushed                              | GHCR tags produced                                         |
| --------------------------------------- | ---------------------------------------------------------- |
| `vX.Y.Z` (stable)                       | `:vX.Y.Z` + `:X.Y` (floating minor) + `:latest`            |
| `vX.Y.Z-rc.N` / `-beta.N` (pre-release) | `:vX.Y.Z-…` + `:beta` (pre-release stays out of `:latest`) |

Only the latest stable line receives security back-ports (see [`SECURITY.md`](SECURITY.md)).

### Conventional commits

Commit subjects follow [Conventional Commits](https://www.conventionalcommits.org/) and are validated by `commitlint` in CI. Allowed types: `feat`, `fix`, `refactor`, `perf`, `docs`, `style`, `test`, `build`, `ci`, `chore`, `revert`.

End-user-visible changes also need an entry under the relevant `[Unreleased]` section, mirrored FR ↔ EN. Keep entries short (~12 words) and user-facing — implementation detail belongs in the commit body, not the changelog.

---

## Secrets

- **Never** commit secrets (API keys, passwords, tokens). Use environment variables.
- `.env` is gitignored. `.env.example` documents every variable the backend reads.
- If a secret leaks, revoke it **immediately** at the provider, then purge it from Git history.

---

## Updating this file

When a workflow convention changes (a new hook is activated, a test runner changes, a coding rule evolves…), update this file **in the same commit**. Stale docs help nobody.

---

## Questions

- **Bug reports & feature requests** — open a GitHub issue using the templates in `.github/ISSUE_TEMPLATE/`.
- **Discussions, help, ideas** — use [GitHub Discussions](https://github.com/KeeperD93/mediakeeper/discussions) or the project's Discord (link in the [README](README.md)).
- **Security disclosures** — see [`SECURITY.md`](SECURITY.md).
