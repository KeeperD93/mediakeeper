<p align="center">
  <img src="frontend/public/assets/icons/mediakeeper_banner.png" width="640" alt="MediaKeeper">
</p>

<p align="center">
  <b>English</b> · <a href="README-fr.md">Français</a>
</p>

<p align="center">
  <i>Open-source self-hosted media library companion: dashboard, request portal, achievements, duplicates, missing-content tracking, statistics, subtitles and more.</i>
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: GPL v3+" src="https://img.shields.io/badge/license-GPL%20v3%2B-blue.svg"></a>
  <a href="https://github.com/KeeperD93/mediakeeper/actions/workflows/backend.yml"><img alt="Backend CI" src="https://github.com/KeeperD93/mediakeeper/actions/workflows/backend.yml/badge.svg"></a>
  <a href="https://github.com/KeeperD93/mediakeeper/actions/workflows/frontend.yml"><img alt="Frontend CI" src="https://github.com/KeeperD93/mediakeeper/actions/workflows/frontend.yml/badge.svg"></a>
  <a href="https://github.com/KeeperD93/mediakeeper/actions/workflows/security.yml"><img alt="Security" src="https://github.com/KeeperD93/mediakeeper/actions/workflows/security.yml/badge.svg"></a>
  <a href="https://discord.gg/A2hyNUUn6a"><img alt="Discord" src="https://img.shields.io/discord/1507137232941617234?label=Discord&logo=discord&color=5865F2&logoColor=white"></a>
  <a href="https://ko-fi.com/keeperd93"><img alt="Ko-fi" src="https://img.shields.io/badge/Ko--fi-Support-FF5E5B?logo=ko-fi&logoColor=white"></a>
  <img alt="AI-assisted" src="https://img.shields.io/badge/AI--assisted-Yes-8A2BE2">
</p>

<p align="center">
  <a href="#getting-started"><b>Quickstart</b></a> ·
  <a href="#why-mediakeeper">Why</a> ·
  <a href="#highlights">Highlights</a> ·
  <a href="#features">Features</a> ·
  <a href="https://github.com/KeeperD93/mediakeeper/wiki">Docs</a> ·
  <a href="https://discord.gg/A2hyNUUn6a">Discord</a> ·
  <a href="https://ko-fi.com/keeperd93">Support</a>
</p>

---

> [!WARNING]
> **Under active development - not yet stable.** MediaKeeper is on its `v1.0.0-rc.x` line, ahead of the first stable `v1.0.0`. Expect changes and a few bugs. To be safe, don't install it on your production data.
> Pin an immutable tag (e.g. `ghcr.io/keeperd93/mediakeeper:vX.Y.Z-rc.N`) rather than `:latest` if you need reproducible behaviour.

---

## What is MediaKeeper?

MediaKeeper sits next to your Emby server and gives two audiences their own surface. Administrators get a back-office to run the library: duplicates, media health, missing-episode tracking, file management (renames, moves, folder creation…), subtitles, Emby user management, and much more. The people you share Emby with get a Portal where they browse the catalogue, request titles, earn trophies, can create movie nights, open tickets, build playlists, get a chat, and much more. It ships as one Docker container with PostgreSQL embedded, so there is no external database to wire up. All available on desktop and mobile.

---

## Why MediaKeeper?

Most tools in this space do one job - request management, library stats, or media cleanup. MediaKeeper combines an administrator back-office and a gamified viewer Portal in a single container, with a few things you won't easily find elsewhere.

| Capability                                                          | MediaKeeper | Typical companion   |
| ------------------------------------------------------------------- | :---------: | :-----------------: |
| Gamification - achievements, XP, levels, monthly leaderboard        |     ✅      |         ✗          |
| Shared movie nights with a virtual cinema room                      |     ✅      |         ✗          |
| Realtime chat, collaborative lists, public viewer profiles          |     ✅      |         ✗          |
| Social request Portal (quotas, blacklist, moderation)               |     ✅      |  Often a bare form  |
| Admin depth - duplicates, library health, watchlist, media manager  |     ✅      |       Partial       |
| User lifecycle - access windows & dated account expiry              |     ✅      |       Partial       |
| Single container with embedded PostgreSQL                           |     ✅      | External DB common  |
| Bilingual UI (EN + FR) with strict parity                           |     ✅      |       Varies        |
| Multi-arch image (amd64 + arm64)                                    |     ✅      |       Varies        |
| GDPR opt-in tooling (per-user export, lifecycle deletion)           |     ✅      |         ✗          |

> Compared against the general category of self-hosted media-server companions, not any specific product - capabilities vary by tool and evolve over time.

---

## Highlights

- **Achievements & XP**: earn 160+ trophies across many families, level up an XP system, and compete on a monthly leaderboard.
- **Shared movie nights**: schedule events in a virtual cinema room, with marathon mode and realtime presence.
- **Request Portal**: viewers ask for films, shows or seasons; quotas, blacklist, auto-cleanup and admin moderation are wired in, not a bare contact form.
- **Single container**: everything runs from one Docker image with embedded PostgreSQL, no external database to provision or back up separately.
- **Admin depth**: live dashboard, duplicate detection, library health checks, a missing-season watchlist and a desktop Media Manager.
- **User management**: give each user an Emby access window that expires on a date you choose (or never), with one-click extensions and optional auto-disable of lapsed accounts on both Emby and MediaKeeper; plus roles, soft-delete and an audit log.
- **Social Portal**: realtime chat with moderation, collaborative lists, public viewer profiles, tickets and a daily digest.
- **Bilingual & portable**: strict EN/FR parity across the UI, on a multi-arch image that runs natively on amd64 and arm64 (Synology, Raspberry Pi, x86).
- **GDPR opt-in**: per-user data export, admin-editable privacy text and a two-step account deletion.

---

## Preview

<p align="center">
  <!-- screenshot: admin dashboard (widgets, ribbon, activity feed) — paste a 1200-1600px wide image here -->
  <br>
  <em>Admin dashboard</em>
</p>

<p align="center">
  <!-- screenshot: portal home (hero strip, lists, posters) — paste a 1200-1600px wide image here -->
  <br>
  <em>Portal viewer</em>
</p>

---

## Features

The highlights are the short version. Here is the full scope by surface - the fine detail lives in the app itself.

<details>
<summary><b>Admin back-office</b> — for the administrator who runs the Emby instance</summary>

<br>

- **Dashboard**: live stats, services health, an activity feed and a customizable widget layout
- **Statistics**: users, libraries and plays, with mobile-readable charts
- **Health check**: scan the library for problems, grouped by severity, with posters
- **Duplicates** — rule-based detection with history, an ignore list and restore
- **Watchlist**: series tracking with missing-season alerts and audio-language tags
- **Media Manager** (desktop): browse, move, rename with TMDB help, tag and dedupe on disk
- **Subtitles**: OpenSubtitles batch download, plus removal of unwanted tracks on disk
- **Users**: Emby access windows with dated expiry, roles & permissions, requests quota, soft-delete, audit log and per-user GDPR export
- **Requests**: moderate viewer requests with filters, bulk actions and configurable auto-cleanup
- **Notifications**: Discord notifications for several kinds of events. More integrations will be added later.
- **Configuration**: a panel of tools to manage/configure your user request portal.

</details>

<details>
<summary><b>Portal viewer</b> — for the people you share Emby with</summary>

<br>

- **Discover**: Trending, Popular, Top-rated, by provider and personalised recommendations, with instant TMDB search
- **Requests**: submit movies, shows or seasons, with quota tracking and clear status feedback
- **Movie nights**: shared cinema events in a virtual room, with marathon mode and realtime presence
- **Lists**: public, private or collaborative, tied to the Curator and Librarian trophy families
- **Achievements & XP**: trophies across many families, an XP and level system, and a monthly leaderboard
- **Statistics**: access to your own statistics
- **Realtime chat**: moderated, with a persistent unread counter and message reporting
- **Tickets**: report a problem on a precise movie, series, season or episode
- **Identity**: custom username, avatar (your Emby one or your own upload) and cosmetic titles
- **Public profiles**, a **daily digest**, **in-app news** and an admin-editable **help center**

</details>

<details>
<summary><b>Cross-cutting</b>: platform, security, accessibility and i18n</summary>

<br>

- **Bilingual UI** (English + French) with strict locale parity
- **Single Docker container** with embedded PostgreSQL; an optional separate worker for production; multi-arch (amd64 + arm64)
- **Defensive security**: separate admin/portal sessions, CSRF protection, rate-limited login, encrypted secrets at rest, log redaction and a security CI pipeline
- **Accessibility**: focus traps, ARIA labels, keyboard navigation, reduced-motion support and skip-to-main
- **Notifications**: an in-app bell with admin-pushed messages, plus Discord webhooks
- **GDPR opt-in**: per-user export, admin-editable privacy text and two-step deletion

</details>

For the full feature catalogue and version history, see the [Wiki](https://github.com/KeeperD93/mediakeeper/wiki) and the changelogs ([admin EN](backend/CHANGELOG_EN.md) · [portal EN](backend/CHANGELOG_PORTAL_EN.md)).

---

## Getting started

### Quickstart - pull the published image

The fastest way is to install the pre-built image from GitHub Container Registry. No clone, no build:

```sh
mkdir mediakeeper && cd mediakeeper
curl -O https://raw.githubusercontent.com/KeeperD93/mediakeeper/main/docker-compose.prod.yml
docker compose -f docker-compose.prod.yml up -d
```

The image is multi-arch (`linux/amd64` + `linux/arm64`) so it runs natively on Synology DSM, Raspberry Pi, traditional x86 servers, etc.

<details>
<summary>Image tags and building from source</summary>

<br>

**Available image tags:**

| Tag       | Pointer                                       | Recommended for                      |
| --------- | --------------------------------------------- | ------------------------------------ |
| `:latest` | most recent stable release                    | everyday self-hosters                |
| `:beta`   | most recent pre-release / release-candidate   | early adopters, testing              |
| `:vX.Y.Z` | exact release (immutable)                     | reproducible deployments, CI pinning |
| `:X.Y`    | floats on the X.Y patch series (e.g. `:1.0`)  | following a single minor line        |

### Alternative — clone and build from source

For contributors or anyone wanting bleeding-edge `main`:

```sh
git clone https://github.com/KeeperD93/mediakeeper.git
cd mediakeeper
docker compose up -d
```

This uses `docker-compose.yml` (with `build: .`) and compiles a fresh image from the local source.

</details>

### First boot

**No `.env` required for a first boot**. MediaKeeper auto-generates everything sensitive on first startup and persists it under `/data/`:

- the PostgreSQL password,
- the JWT secret,
- the encryption key for secrets stored in the database,
- an initial **admin** account with a random password printed once in the container logs.

Read the initial admin password from the logs as soon as the container is up:

```sh
docker compose logs mediakeeper | grep -A 6 "ADMIN ACCOUNT CREATED"
```

(Use `docker compose -f docker-compose.prod.yml logs mediakeeper` instead if you started from the GHCR quickstart.)

> [!IMPORTANT]
> Capture this password immediately. It is **not** persisted to `/data/`. If you miss it (terminal closed, logs rotated), recover with the CLI helper — see [`docs/operations/admin-recovery.md`](docs/operations/admin-recovery.md).

Then open `http://<host>:8888`, sign in as `admin` with that password - a password change is forced on first connection.

**Need to customise?** Copy `.env.example` to `.env` and adjust the variables you need (e.g. `TMDB_API_KEY`, `FRONTEND_ORIGIN`, `MEDIAKEEPER_PATH_ROOTS`) before running `docker compose up -d`. Auto-generated values are respected on subsequent boots.

The application runs database migrations automatically at boot.

Updating an existing install? See [`docs/operations/updating.md`](docs/operations/updating.md).

For Synology DSM, reverse-proxy setups, TLS deployment and advanced configuration, see the [Wiki](https://github.com/KeeperD93/mediakeeper/wiki) and the operations runbooks in [`docs/operations/`](docs/operations/).

---

## Documentation

| Surface                                                                    | Where                                                                                                                                                                                                                    |
| -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| User wiki                                                                  | https://github.com/KeeperD93/mediakeeper/wiki                                                                                                                                                                            |
| Operations runbooks (admin / sysadmin)                                     | [`docs/operations/`](docs/operations/)                                                                                                                                                                                   |
| Deployment guides (Caddy, Traefik, Nginx Proxy Manager, LAN, Synology DSM) | [`docs/deployment/`](docs/deployment/)                                                                                                                                                                                   |
| Contributing                                                               | [`CONTRIBUTING.md`](CONTRIBUTING.md)                                                                                                                                                                                     |
| Security policy                                                            | [`SECURITY.md`](SECURITY.md)                                                                                                                                                                                             |
| Code of conduct                                                            | [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)                                                                                                                                                                               |
| Third-party licences                                                       | [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md)                                                                                                                                                                     |
| Changelog                                                                  | Admin: [`CHANGELOG_FR`](backend/CHANGELOG_FR.md) · [`CHANGELOG_EN`](backend/CHANGELOG_EN.md) · Portal: [`CHANGELOG_PORTAL_FR`](backend/CHANGELOG_PORTAL_FR.md) · [`CHANGELOG_PORTAL_EN`](backend/CHANGELOG_PORTAL_EN.md) |

---

## Community & support

- **Discord**: [discord.gg/A2hyNUUn6a](https://discord.gg/A2hyNUUn6a)
- **GitHub Discussions**: https://github.com/KeeperD93/mediakeeper/discussions
- **Roadmap**: public board of what's planned: https://github.com/users/KeeperD93/projects/1
- **Bug reports & feature requests**: https://github.com/KeeperD93/mediakeeper/issues
- **Security disclosures**: see [`SECURITY.md`](SECURITY.md); please do **not** open a public issue

---

## ☕ Buy me a coffee

MediaKeeper is free and open-source. If you find it useful, a coffee goes a long way:

- **Ko-fi**: [ko-fi.com/keeperd93](https://ko-fi.com/keeperd93) - one-time tips or recurring memberships, PayPal and cards accepted
- **Star the repo**: every star helps visibility on GitHub

---

## Contributing

Pull requests are welcome. Before you start, read [`CONTRIBUTING.md`](CONTRIBUTING.md) and the [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

In short:

1. Fork the repo and create a feature branch (`feat/...`, `fix/...`, `refactor/...`).
2. Follow the coding conventions in `CONTRIBUTING.md` (i18n, mobile-first, design tokens, file size).
3. Add tests for any new endpoint or composable.
4. Commit with [Conventional Commits](https://www.conventionalcommits.org/) format.
5. Open the PR; CI must pass before review.

---

## AI-assisted development

MediaKeeper is developed with AI assistance. Every change is reviewed, tested and committed by the maintainer.

---

## Tech stack

<details>
<summary>Frontend, backend, database and quality tooling</summary>

<br>

| Layer        | Tech                                                                                                |
| ------------ | --------------------------------------------------------------------------------------------------- |
| **Frontend** | Vue, Vue Router, vue-i18n, Vite, PrimeVue, Chart.js, lucide-vue-next, TipTap                        |
| **Backend**  | FastAPI (Python), SQLAlchemy (async), Alembic, PyJWT, bcrypt, httpx, slowapi, cryptography, bleach  |
| **Database** | PostgreSQL (embedded in the image), SQLite for tests                                                |
| **Quality**  | ESLint, Prettier, Stylelint, Vitest, pytest, Husky + commitlint, ruff, bandit, semgrep, pip-audit, npm audit |

</details>

---

## Attribution

This product uses the **TMDB API** but is not endorsed or certified by TMDB. See https://www.themoviedb.org for the data source.

MediaKeeper integrates with **Emby**, **OpenSubtitles**, **Discord** webhooks and (optionally) **Imgur**. Each provider's terms apply when those features are enabled. Full breakdown in [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).

---

## License

MediaKeeper is published under the **GNU General Public License v3.0 or later** — see [`LICENSE`](LICENSE).
