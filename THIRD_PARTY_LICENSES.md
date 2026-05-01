# Third-party licences

MediaKeeper is distributed under the **GNU General Public License v3.0 or later** (see `LICENSE`).

This document lists the main third-party components shipped with or required by MediaKeeper, the licence each one is published under, and how they relate to the project. It is meant as a starting point for due-diligence reviews; for the authoritative licence text always consult the upstream project.

The list is built from `frontend/package.json` and `backend/requirements.txt`. Transitive dependencies are not enumerated here — `npm ls` and `pip show` give the full tree on a given install.

> **Note on licence identifiers.** SPDX identifiers below are the most commonly published licences for each project; some packages are dual-licensed or have evolved over time. When in doubt, check the upstream `LICENSE` file in the installed version.

---

## Frontend runtime dependencies (`frontend/package.json` → `dependencies`)

| Package | SPDX licence | Notes |
|---|---|---|
| `vue` | MIT | Vue 3 framework. |
| `vue-router` | MIT | Routing. |
| `vue-i18n` | MIT | Internationalisation. |
| `@primevue/themes` | MIT | PrimeVue theme system. |
| `primevue` | MIT | PrimeVue components. |
| `primeicons` | MIT | PrimeIcons icon font. |
| `chart.js` | MIT | Charting library used in stats views. |
| `grid-layout-plus` | MIT | Draggable grid layout. |
| `lucide-vue-next` | ISC | Lucide icon set, Vue 3 bindings. The Lucide icons themselves are published under the ISC licence. |
| `@tiptap/core` and `@tiptap/extension-*`, `@tiptap/pm`, `@tiptap/starter-kit`, `@tiptap/vue-3` | MIT | Rich-text editor used in admin surfaces. |

## Frontend dev / tooling dependencies (`frontend/package.json` → `devDependencies`)

| Package | SPDX licence | Notes |
|---|---|---|
| `vite` | MIT | Build tool. |
| `@vitejs/plugin-vue` | MIT | Vite plugin for Vue SFCs. |
| `vitest` | MIT | Test runner. |
| `@vitest/coverage-v8` | MIT | Coverage reporter (V8). |
| `@vue/test-utils` | MIT | Vue testing utilities. |
| `vue-tsc` | MIT | Vue type checker. |
| `typescript` | Apache-2.0 | TypeScript compiler. |
| `eslint` and `@eslint/js`, `eslint-plugin-vue`, `eslint-config-prettier`, `eslint-plugin-prettier`, `vue-eslint-parser` | MIT | Linting toolchain. |
| `prettier` | MIT | Code formatter. |
| `stylelint` and `stylelint-config-recommended-vue`, `stylelint-config-standard` | MIT | Stylesheet linter and shared configs. |
| `postcss`, `postcss-html` | MIT | CSS post-processor and HTML adapter. |
| `autoprefixer` | MIT | Vendor-prefixing plugin. |
| `tailwindcss` | MIT | Utility-first CSS framework (in the process of being phased out — see roadmap). |
| `globals` | MIT | Globals reference data for ESLint. |
| `husky` | MIT | Git hooks runner. |
| `lint-staged` | MIT | Run linters on staged files. |
| `jsdom` | MIT | DOM implementation used by Vitest. |
| `depcheck` | MIT | Unused-dependency scanner. |
| `openapi-typescript` | MIT | Generates TypeScript types from OpenAPI. |
| `lighthouse` | Apache-2.0 | Performance audits. |
| `@lhci/cli` | Apache-2.0 | Lighthouse CI runner. |
| `@playwright/test` | Apache-2.0 | End-to-end test runner. |
| `@axe-core/playwright` | MPL-2.0 | Accessibility testing engine, Playwright integration. |
| `autocannon` | MIT | HTTP benchmarking tool. |
| `@commitlint/cli`, `@commitlint/config-conventional` | MIT | Conventional Commits linter. |
| `@types/node` | MIT | Node.js type definitions. |

## Backend runtime dependencies (`backend/requirements.txt`)

| Package | SPDX licence | Notes |
|---|---|---|
| `fastapi` | MIT | Web framework. |
| `uvicorn[standard]` | BSD-3-Clause | ASGI server (the `[standard]` extras pull in additional libraries with their own licences). |
| `sqlalchemy` | MIT | ORM and SQL toolkit. |
| `asyncpg` | Apache-2.0 | Async PostgreSQL driver. |
| `aiosqlite` | MIT | Async SQLite driver, used in the test suite. |
| `pydantic` | MIT | Data validation and settings. |
| `httpx` | BSD-3-Clause | HTTP client. |
| `python-dotenv` | BSD-3-Clause | `.env` loader. |
| `psutil` | BSD-3-Clause | System metrics. |
| `bcrypt` | Apache-2.0 | Password hashing. |
| `PyJWT[crypto]` | MIT | JWT encoding / decoding. |
| `python-multipart` | Apache-2.0 | Multipart form parser. |
| `aiofiles` | Apache-2.0 | Async file I/O. |
| `alembic` | MIT | Database migration tool. |
| `slowapi` | MIT | Rate limiting for FastAPI. |
| `pytest` | MIT | Test framework. |
| `pytest-asyncio` | Apache-2.0 | Async test support for pytest. |
| `pytest-cov` | MIT | Coverage plugin for pytest. |
| `chardet` | LGPL-2.1-or-later | Character-encoding detector (subtitles). |
| `cryptography` | Apache-2.0 OR BSD-3-Clause | Cryptographic primitives (Fernet). Dual-licensed; see upstream `LICENSE`. |
| `bleach[css]` | Apache-2.0 | HTML sanitiser. |

---

## External tools and runtimes

These are not Python or npm packages, but MediaKeeper relies on them at runtime or in containerised builds. They are not redistributed in source form by this repository.

| Tool | Licence | How MediaKeeper uses it |
|---|---|---|
| **Python** | PSF License | Backend runtime. The repository does not redistribute the Python interpreter. |
| **Node.js** | MIT (and bundled components) | Frontend build tooling. Not redistributed by this repository. |
| **PostgreSQL 16** | PostgreSQL Licence (BSD-style) | Database engine bundled with the official Docker image used at boot. |
| **FFmpeg** | LGPL v2.1-or-later, or GPL v2-or-later, depending on the build | Invoked as an external binary for media probing and processing. The Docker image used in deployment installs FFmpeg from the distribution package; whether that build is LGPL or GPL depends on the package and configure flags chosen by the distribution maintainer. **Verify the licence of the specific FFmpeg build you ship before redistribution.** This repository does not vendor FFmpeg sources or binaries. |
| **Docker** images / `entrypoint.sh` / `Dockerfile` | Project-specific (GPL-3.0-or-later, see `LICENSE`) | The Dockerfile and helper scripts are part of MediaKeeper. The base images they `FROM` carry their own licences (see the corresponding upstream Docker Hub pages). |

## External services / APIs (data, not code)

MediaKeeper queries external APIs at runtime. These services are **not** distributed with the repository, but the data they return is governed by their respective terms.

| Service | Terms |
|---|---|
| **The Movie Database (TMDB) API** | TMDB API terms of use. MediaKeeper uses TMDB as a data source but is not endorsed or certified by TMDB. An attribution notice is shown in the application footer. |
| **OpenSubtitles** | OpenSubtitles API terms of use. |
| **Discord webhooks** | Discord developer terms. |
| **Imgur** (when configured) | Imgur API terms. |

These services are integration points, not redistributed assets, and their licence does not propagate to MediaKeeper itself.

---

## How to verify the licence of an installed dependency

```sh
# Python
pip show <package> | findstr /I license
# or, to enumerate everything:
pip-licenses

# Node
npm ls --json <package>
# or, to enumerate everything:
npx license-checker --summary
```

If you spot a discrepancy between this document and the upstream licence — especially if a package has changed licence since this list was last reviewed — please open a pull request or contact the maintainers (see `SECURITY.md` for the contact channel).
