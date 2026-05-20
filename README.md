<p align="center">
  <img src="frontend/public/assets/icons/mediakeeper_banner.png" width="640" alt="MediaKeeper">
</p>

<p align="center">
  <i>Open-source self-hosted media library companion: dashboard, request portal, achievements, backups and more.</i>
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: GPL v3+" src="https://img.shields.io/badge/license-GPL%20v3%2B-blue.svg"></a>
  <a href="https://github.com/KeeperD93/mediakeeper/actions/workflows/backend.yml"><img alt="Backend CI" src="https://github.com/KeeperD93/mediakeeper/actions/workflows/backend.yml/badge.svg"></a>
  <a href="https://github.com/KeeperD93/mediakeeper/actions/workflows/frontend.yml"><img alt="Frontend CI" src="https://github.com/KeeperD93/mediakeeper/actions/workflows/frontend.yml/badge.svg"></a>
  <a href="https://github.com/KeeperD93/mediakeeper/actions/workflows/security.yml"><img alt="Security" src="https://github.com/KeeperD93/mediakeeper/actions/workflows/security.yml/badge.svg"></a>
  <a href="<DISCORD_INVITE>"><img alt="Discord" src="https://img.shields.io/badge/Discord-Join-5865F2?logo=discord&logoColor=white"></a>
  <img alt="AI-assisted" src="https://img.shields.io/badge/AI--assisted-Yes-8A2BE2">
</p>

---

> [!WARNING]
> **Under active development — not yet stable.**
>
> MediaKeeper is on its `0.9.x` line, ahead of the first stable `1.0.0` release.
> Expect schema changes, breaking refactors, missing pieces and rough edges.
> Do not point it at production data you cannot afford to lose, and pin a
> specific image tag rather than `latest` when deploying.

---

## 🎯 What is MediaKeeper?

MediaKeeper is a **single-container, self-hosted companion** for a small Emby instance. It complements Emby with two surfaces in one app:

- A polished **admin back-office** for managing your library, scanning duplicates, watching activity, scheduling jobs and running backups.
- A friendly **Portal viewer** designed for the people you share Emby with — catalogue browsing, requests, achievements, lists, daily digests, news, tickets and shared movie nights.

Everything runs from a **single Docker container** with an embedded PostgreSQL 16; no external paid SaaS, no extra services to wire up, no cloud lock-in.

---

## ✨ Key features

### Admin back-office

- **Dashboard** — live stats, services health, activity feed, customizable widget layout
- **Statistics** — users, activity, libraries, charts
- **Health check** — automatic library scan, severity grouping, issue posters
- **Duplicates** — detection rules, history, ignored list, restore
- **Media Manager** (desktop) — browse, move, rename, tag, dedupe directly on disk
- **Scheduler** — recurring tasks with cache, manual triggers
- **Backups** — manual ZIPs + scheduled jobs + drill-tested restore procedure
- **Watchlist** — series tracking (missing seasons), monitoring rules

### Portal viewer (the experience for your users)

- **Browse** — catalogue, hero strip with auto-rotating slideshow, recent releases
- **Search** — instant TMDB suggestions with 5-min cache, history, ⌘K shortcut
- **Requests** — submit movies, shows or seasons; quota tracking and status feedback
- **Achievements & XP** — 160+ trophies (community, watching, marathons, secrets, milestones); levels up to 50
- **Movie nights** — scheduled events with a virtual cinema room, marathon mode, realtime presence, per-event capacity
- **Lists** — public, private or collaborative lists, with curator and librarian achievements
- **Profile** — custom avatar, public profile page, leaderboard ranking, ticket history
- **Chat** — realtime room with moderation and unread persistence
- **Help center** — 15+ articles editable by admins, full-screen reader

### Cross-cutting

- **Bilingual UI** (French + English) with strict locale parity
- **Single Docker container**, multi-arch ready (planned: `amd64` + `arm64`)
- **Defensive auth** — JWT scope separation (admin / portal), CSRF double-submit, rate-limited login, Fernet-encrypted secrets at rest
- **Accessibility** — focus traps on modals, ARIA labels, `prefers-reduced-motion` aware
- **Notifications** — in-app bell + Discord webhooks
- **GDPR opt-in** — user export, privacy text, lifecycle deletion

---

## 📸 Preview

### Admin dashboard

<!-- screenshot placeholder: admin dashboard (widgets, ribbon, activity feed) — paste a 1200-1600px wide image here -->

### Portal viewer

<!-- screenshot placeholder: portal home (hero strip, lists, posters) — paste a 1200-1600px wide image here -->

---

## 🚀 Getting started

The recommended way to run MediaKeeper is through Docker Compose.

```sh
git clone https://github.com/KeeperD93/mediakeeper.git
cd mediakeeper
cp .env.example .env
# Edit .env — at minimum set JWT_SECRET_KEY (≥ 32 random bytes).
docker compose up -d
```

Then open `http://<host>:8888` in your browser. The first admin login uses the bootstrap credentials from `.env`; you will be asked to change the password on first connection.

The application runs `alembic upgrade head` at boot, so database migrations are applied automatically.

For Synology DSM, reverse-proxy setups, TLS deployment and advanced configuration, see the [Wiki](https://github.com/KeeperD93/mediakeeper/wiki) and the operations runbooks in [`docs/operations/`](docs/operations/).

---

## 📖 Documentation

| Surface | Where |
|---|---|
| User wiki | https://github.com/KeeperD93/mediakeeper/wiki |
| Operations runbooks (admin / sysadmin) | [`docs/operations/`](docs/operations/) |
| Deployment guides (Caddy, Traefik, Nginx Proxy Manager, LAN, Synology DSM) | [`docs/deployment/`](docs/deployment/) |
| Contributing | [`CONTRIBUTING.md`](CONTRIBUTING.md) |
| Security policy | [`SECURITY.md`](SECURITY.md) |
| Code of conduct | [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) |
| Third-party licences | [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md) |
| Changelog | Admin: [`CHANGELOG_FR`](backend/CHANGELOG_FR.md) · [`CHANGELOG_EN`](backend/CHANGELOG_EN.md) · Portal: [`CHANGELOG_PORTAL_FR`](backend/CHANGELOG_PORTAL_FR.md) · [`CHANGELOG_PORTAL_EN`](backend/CHANGELOG_PORTAL_EN.md) |

---

## 💬 Community & support

- **Discord** — `<DISCORD_INVITE>` *(coming soon)*
- **GitHub Discussions** — https://github.com/KeeperD93/mediakeeper/discussions
- **Bug reports & feature requests** — https://github.com/KeeperD93/mediakeeper/issues
- **Security disclosures** — see [`SECURITY.md`](SECURITY.md); please do **not** open a public issue

---

## 🤝 Contributing

Pull requests are welcome. Before you start, please read [`CONTRIBUTING.md`](CONTRIBUTING.md) and the [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

In short:

1. Fork the repo and create a feature branch (`feat/...`, `fix/...`, `refactor/...`).
2. Follow the coding conventions in `CONTRIBUTING.md` (i18n, mobile-first, design tokens, file size).
3. Add tests for any new endpoint or composable.
4. Commit with [Conventional Commits](https://www.conventionalcommits.org/) format.
5. Open the PR; CI must pass before review.

---

## 🤖 AI-assisted development

MediaKeeper is built with significant AI assistance — primarily **Claude** (Anthropic) used through **Claude Code**. Every change is reviewed, tested and committed by the maintainer; the AI accelerates iteration and helps with research, refactoring and documentation, but it does not replace human judgement, review or accountability.

This note exists for transparency: contributors and users should know how the project is built. The historical record (commits, PR bodies, changelogs) stays human-authored — there is no AI co-author signature on commits.

---

## 📦 Tech stack

| Layer | Tech |
|---|---|
| **Frontend** | Vue 3 (`<script setup>`), Vue Router 5, vue-i18n 11, Vite 6, PrimeVue 4, Chart.js 4, lucide-vue-next, TipTap |
| **Backend** | FastAPI (Python 3.12), SQLAlchemy 2 (async), Alembic, PyJWT, bcrypt, httpx, slowapi, cryptography (Fernet), bleach |
| **Database** | PostgreSQL 16 (production, embedded in the Docker image), SQLite (tests) |
| **Quality** | ESLint, Prettier, Stylelint, Vitest, pytest + pytest-cov, Husky + commitlint, ruff, bandit, semgrep, pip-audit, npm audit |

---

## 🔌 Attribution

This product uses the **TMDB API** but is not endorsed or certified by TMDB. See https://www.themoviedb.org for the data source.

MediaKeeper integrates with **Emby**, **OpenSubtitles**, **Discord** webhooks and (optionally) **Imgur**. Each provider's terms apply when those features are enabled. Full breakdown in [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).

---

## 📝 License

MediaKeeper is published under the **GNU General Public License v3.0 or later** — see [`LICENSE`](LICENSE).
