# MediaKeeper

> [!WARNING]
> **Under active development — not yet stable.**
>
> MediaKeeper is on its `0.9.x` line, ahead of the first stable `1.0.0` release.
> Expect schema changes, breaking refactors, missing pieces and rough edges.
> Do not point it at production data you cannot afford to lose, and pin a
> specific image tag rather than `latest` when deploying.

Self-hosted companion for a small Emby instance: an admin back-office, a Portal viewer for friends and family, achievements and XP, a Media Manager, daily digests, request handling and more.

## Highlights

- **Two surfaces in one app**
  - **Admin / back-office**: dashboard, statistics, watchlist, Media Manager, scheduler, backups, settings.
  - **Portal**: a friendlier viewer surface aimed at the people who use the Emby instance — catalogue browsing, requests, achievements, XP, profile, lists, daily digest, news, tickets.
- **Tight Emby integration** for sessions, library and metadata.
- **TMDB-backed metadata cascade** (synopsis, trailers, videos) with language fallbacks (user → English → original → language-agnostic).
- **Achievements & XP**: 150+ achievements, secret trophies, levels up to 50.
- **Media Manager** (desktop-only): browse, move, rename, tag and de-duplicate media files.
- **Notifications**: in-app and Discord webhooks, with a debounce policy.
- **Self-hosted by design**: a single Docker container, embedded PostgreSQL 16, no external paid SaaS required.

## Tech stack at a glance

| Layer | Tech |
|---|---|
| Frontend | Vue 3 (`<script setup>`), Vue Router 5, vue-i18n 11, Vite, PrimeVue 4, Chart.js, lucide-vue-next, TipTap |
| Backend | FastAPI, SQLAlchemy 2 (async), Alembic, PyJWT, bcrypt, httpx, slowapi, cryptography (Fernet), bleach |
| Database | PostgreSQL 16 (production, embedded in the Docker image), SQLite (tests) |
| Deployment | Single Docker container, port 8888, healthcheck `/api/health?full=1` |
| Quality | ESLint, Prettier, Stylelint, Vitest, pytest + pytest-cov, Husky + commitlint |

For the full code map, see [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Quick start (Docker)

The recommended way to run MediaKeeper is through Docker Compose.

```sh
git clone <repo-url> mediakeeper
cd mediakeeper

cp .env.example .env
# Edit .env to set MK_JWT_SECRET (≥ 32 bytes), database password,
# admin bootstrap credentials, etc.

docker compose up -d
```

Then open `http://<host>:8888` in your browser. The first admin login uses the bootstrap credentials defined in `.env`; you will be asked to change the password on first connection.

The application runs `alembic upgrade head` at boot, so database migrations are applied automatically.

## Local development

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full development workflow (lint, tests, Conventional Commits, Husky hooks, PR template).

Short version:

```sh
# Frontend dev server (with hot reload)
cd frontend
npm install
npm run dev          # http://localhost:5173

# Backend (locally, without Docker)
cd ../backend
pip install -r requirements.txt
uvicorn main:app --reload

# OR keep the backend in Docker and just iterate on the frontend
cd ..
docker compose up -d
cd frontend && npm run dev
```

## Documentation

| File | What it covers |
|---|---|
| [`README.md`](README.md) | This file — overview and pointers. |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Code map: layers, modules, data flow, design system, auth scopes. |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Developer workflow: setup, lint, tests, commits, PRs, the public coding-conventions checklist, adding a language or a dependency. |
| [`SECURITY.md`](SECURITY.md) | Security policy and how to report a vulnerability privately. |
| [`docs/operations/`](docs/operations/) | Operator runbooks: restore procedure ([`backup-restore.md`](docs/operations/backup-restore.md)), incident response ([`runbook-incidents.md`](docs/operations/runbook-incidents.md)), runtime monitoring ([`monitoring.md`](docs/operations/monitoring.md)) and TLS deployment ([`tls-deployment.md`](docs/operations/tls-deployment.md)). |
| [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md) | Licences of the main third-party dependencies. |

## Attribution

This product uses the **TMDB API** but is not endorsed or certified by TMDB. See `https://www.themoviedb.org` for the data source.

MediaKeeper also integrates with OpenSubtitles, Discord webhooks and (optionally) Imgur. Each provider's terms apply when those features are enabled. See [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md#external-services--apis-data-not-code) for the list.

## Licences / Third-party licences

MediaKeeper is published under the **GNU General Public License v3.0 or later** — see [`LICENSE`](LICENSE).

A summary of the third-party libraries used by the project is in [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md). Notable points:

- Most npm and Python dependencies are MIT, BSD or Apache 2.0.
- `lucide-vue-next` (icons) is published under the ISC licence.
- **FFmpeg** is invoked as an external binary; depending on the build it ships under LGPL v2.1-or-later or GPL v2-or-later. Verify the licence of the FFmpeg build you redistribute before publishing your own image.
- The TMDB / OpenSubtitles / Discord / Imgur APIs are external services; MediaKeeper integrates with them but does not redistribute their data.

## Reporting issues

- **Security**: see [`SECURITY.md`](SECURITY.md) — please do **not** open a public issue for security problems.
- **Bugs and feature requests**: open a GitHub issue using the templates in `.github/ISSUE_TEMPLATE/`.
