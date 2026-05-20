# Contributing to MediaKeeper

> This file describes the **workflow** (dev setup, lint, tests, commits, pull requests) and a short, public **coding-conventions checklist** every contributor is expected to follow. The architecture is described in `ARCHITECTURE.md`.

---

## Prerequisites

- **Node.js** ≥ 20 and **npm** ≥ 10 (frontend).
- **Python** ≥ 3.11 (backend, when running it locally — otherwise use Docker).
- **Docker** + **docker compose** (recommended for backend in a prod-like setup).
- **Git**.

---

## Initial setup

```sh
git clone <repo-url> mediakeeper
cd mediakeeper

# Frontend
cd frontend
npm install
cp .env.example .env   # adjust if needed
npm run dev            # http://localhost:5173

# Backend (local, no Docker)
cd ../backend
pip install -r requirements.txt
uvicorn main:app --reload

# OR backend in Docker
cd ..
docker compose up -d
```

To activate the commit hooks (Husky + commitlint):

```sh
mkdir -p .husky
cp .husky-templates/pre-commit .husky/pre-commit
cp .husky-templates/commit-msg .husky/commit-msg
chmod +x .husky/*
git config core.hooksPath .husky
```

---

## Coding conventions checklist

These are the rules every PR must follow. They apply equally to features, fixes and refactors.

### Frontend

- **i18n** — every user-facing string goes through `$t('key')` / `t('key')`. Never hardcode FR or EN text in templates or scripts. Add the key to **both** `frontend/src/locales/fr.json` and `frontend/src/locales/en.json` (FR is the source, EN is the mirror).
- **Mobile-first** — default styles target the smallest viewport; widen via `@media (min-width: ...)`. Use only the project breakpoints from `frontend/src/styles/breakpoints.css` (`--bp-sm` … `--bp-3xl`). Touch targets ≥ 44 × 44 px on mobile. `:hover` effects must be wrapped in `@media (hover: hover) { … }`.
- **Overflow safety** — page roots use `overflow-x: clip` (not `hidden`) so a wide descendant cannot trigger mobile auto-zoom-out and the document keeps scrolling vertically.
- **Design tokens** — never hardcode a colour, radius, font size, shadow or spacing if a token exists. Prefer the project token (e.g. `var(--accent-500)`, `var(--radius-btn)`) over a literal value.
- **No inline styles** — `style="..."` attributes are not allowed in templates, except for genuinely runtime-computed values. Move presentational rules to a `<style scoped>` block or to a CSS file under `assets/styles/`.
- **Layered components** — split work between four layers:
  - **Component** (Vue SFC) — presentation, props, events, scoped style.
  - **Composable** (`use*.js`) — reusable logic and shared state.
  - **`useApi`** — the only HTTP boundary (handles JWT refresh, CSRF, 401 redirect). Never call `fetch()` directly from a component.
  - **Constants** (`frontend/src/constants/*.js`) — every shared string (status, slug, event name).
- **Vue scoped CSS** — when extracting styles from a component into `assets/styles/...`, prefix every selector with the component's root class (e.g. `.pt-help-…`) to simulate scoping. Tokens-only values.
- **Icons** — single source `lucide-vue-next`; no inline `<svg>` or hand-drawn `<path>` for an icon Lucide already exposes.
- **TMDB cascade** — when querying TMDB, apply the language fallback `user → English → original language → language-agnostic`. Never hardcode `fr` or `en` as the priority.

### Backend

- One router = one domain. Business logic lives in a service (`services/<domain>_service.py`); a router never talks directly to the database.
- DB migration → a new Alembic file. Do **not** modify an existing migration once it has been applied.
- Errors surfaced to the user are **i18n codes** (e.g. `errors.embyUnreachable`), not full sentences; the frontend translates them.

### Cross-cutting

- **File size** — every applicative file (Vue, JS/TS, Python, CSS) stays at or under **300 lines**. Split before adding features when you reach the limit.
- **Code language** — comments, docstrings, log messages, identifiers are written in English. The `*.fr.json` locales and the `CHANGELOG_FR.md` files are the only French-by-design surfaces.
- **Dates / timezones** — store UTC with timezone, transmit ISO 8601, format on the frontend with `Intl.DateTimeFormat` and the user locale. Never hardcode a timezone or `'fr-FR'`.
- **No third-party brand in changelogs** — write user-facing changelog entries without naming external products, frameworks or "inspired by X" phrasing. Describe the change in product terms.

---

## Development workflow

### 1. Read the conventions above

Before any new code, (re)read the *Coding conventions checklist*.

### 2. Working branch

```sh
git checkout -b feat/my-feature   # or fix/bug-xyz, refactor/…
```

Recommended prefixes: `feat/`, `fix/`, `refactor/`, `docs/`, `chore/`, `perf/`.

### 3. Code

- Use the shared frontend components (`MkSpinner`, `MkEmptyState`, `MkAvatar`, `MkConfirmDialog`) and utility classes (`mk-modal-sheet`, `pt-carousel-arrow`, `pt-edge-fade`) before introducing new ones.
- For backend services, follow the router-thin / service-thick split described above.

### 4. Lint and format

Before each commit:

```sh
cd frontend
npm run lint             # ESLint
npm run stylelint        # stylelint
npm run format           # Prettier
```

Once Husky hooks are active (see *Initial setup*), `git commit` triggers `lint-staged` automatically on staged files.

### 5. Tests

```sh
# Frontend unit tests
cd frontend
npm run test:unit              # single pass
npm run test:unit:watch        # watch mode
npm run test:coverage          # + coverage report

# Backend tests
cd backend
pytest                         # full suite
pytest --cov                   # + coverage
pytest tests/test_auth_login.py -v   # specific file
```

**Every new API endpoint must have at least one test.**

CI runs these tests automatically (see `.github/workflows/`):
- `backend.yml` — pytest + coverage XML on push to `main` and PRs touching `backend/**`.
- `frontend.yml` — ESLint + Stylelint + Prettier check + `vue-tsc` typecheck + Vitest + build, on push to `main` and PRs touching `frontend/**`.
- `commitlint.yml` — Conventional Commits format check on PRs.

### 6. Commit

**Conventional Commits** format (see `commitlint.config.js`):

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `refactor`, `perf`, `docs`, `style`, `test`, `build`, `ci`, `chore`, `revert`.

Examples:

```
feat(portal): add trophy unlock toast
fix(media-manager): handle empty filename in rename batch
refactor(stats): extract StatsUserPopover into composable
chore(deps): bump vite to 6.4.2
```

**Header max length**: 120 characters.

### 7. User-facing changelog

If the change is **visible to end users** (feature, UX fix, new option), add an `[Unreleased]` entry in the relevant changelog (admin or portal, FR + EN mirrored). Entries are short (~12 words max), describe the change in product terms, and never name a third-party brand.

The project ships **two changelog pairs**:
- Admin / back-office: `backend/CHANGELOG_FR.md` ↔ `backend/CHANGELOG_EN.md` (versioned via `APP_VERSION`).
- Portal viewer: `backend/CHANGELOG_PORTAL_FR.md` ↔ `backend/CHANGELOG_PORTAL_EN.md` (versioned via `PORTAL_VERSION`).

A change touching both surfaces is logged in both pairs. **Do not add** an entry for: refactors, internal renames, technical migrations, tests, docs.

### 8. Pull request

```sh
git push origin feat/my-feature
# then open a PR on GitHub
```

In the PR description:
- **What it does** (1–2 sentences).
- **Why** (business context if applicable).
- **How to test** (reproducible steps).
- **Screenshots** if UI changes.
- **Breaking changes** if any.

Every PR must pass CI (lint + tests) before review.

---

## Rebase vs merge

- **Feature branches**: `rebase` onto `main` before merge (linear history).
- **Conflicts**: resolve manually. Do **not** run `git checkout --theirs/--ours` without understanding the consequences.
- **Force push**: only on **your own feature branch**. Never on `main`.

---

## Secrets

- **Never** commit secrets (API keys, passwords, tokens). Use environment variables.
- `.env` is gitignored. `.env.example` documents the required variables.
- If a secret leaks, revoke it **immediately** at the provider, then purge it from Git history.

---

## Adding a dependency

Frontend:
```sh
cd frontend
npm install --save <pkg>        # runtime dependency
npm install --save-dev <pkg>    # dev dependency
```

Backend:
```sh
# Edit backend/requirements.txt manually (pin the version)
# Then rebuild the container OR:
cd backend && pip install -r requirements.txt
```

**Before adding** a dependency:
1. Check that no native or already-installed solution covers the need.
2. Check the frontend bundle impact (`npm run build`) for frontend dependencies.
3. Check the licence is compatible (MIT / Apache 2 / BSD OK — GPL / AGPL needs justification, see `THIRD_PARTY_LICENSES.md`).
4. Check upstream health (recent releases, stars, open issues).

---

## Updating this file

When a workflow convention changes (a new hook is activated, a test runner changes…), update this file **in the same commit**. Stale docs help nobody.

---

## Adding a language (i18n)

The project currently ships **2 locales**: `fr.json` (source) and `en.json` (mirror). To add a new language:

1. Copy `frontend/src/locales/en.json` to `frontend/src/locales/<code>.json` (e.g. `de.json`, `es.json`).
2. Translate **all values** without touching the keys.
3. Register the code in `frontend/src/i18n.js` (loaded locales + native name shown in the picker).
4. Make sure `frontend/scripts/check-integrity.mjs` reports no missing keys.
5. Open a PR titled `feat(i18n): add <language> locale`.

Translation contributions are welcome.

---

## Questions

- **Code map** → `ARCHITECTURE.md`
- **Security policy** → `SECURITY.md`
- **Anything else** → open a GitHub issue.
