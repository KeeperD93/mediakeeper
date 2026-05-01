# Security policy

MediaKeeper is a personal media-management application. We take security reports seriously and aim to acknowledge and address valid issues promptly.

## Supported versions

| Version | Supported |
|---|---|
| `0.9.x` | Yes — current pre-1.0 line |
| `< 0.9` | No — please upgrade before reporting |

The first stable release will be `1.0.0`. Until then, only the latest `0.9.x` minor receives security fixes.

## Reporting a vulnerability

Please **do not open a public issue** for security problems. Use one of the channels below.

### Preferred channel

If GitHub *Private vulnerability reporting* is enabled on the repository (Security tab → "Report a vulnerability"), please use it. Reports stay private until coordinated disclosure.

### Backup channel

Email **[keeperdfr@proton.me](mailto:keeperdfr@proton.me)** with:

- a clear description of the issue,
- the affected version (commit hash if possible),
- steps to reproduce,
- the expected impact and any proof-of-concept,
- whether you would like to be credited in the eventual advisory.

> A dedicated security alias (e.g. `security@…`) may be set up later and will be advertised here when available. In the meantime, the address above is the canonical contact.

### What to expect

| Stage | Target time |
|---|---|
| Acknowledgement of receipt | within 72 hours |
| Initial triage / severity assessment | within 7 days |
| Fix or mitigation plan communicated to the reporter | within 30 days for confirmed issues |
| Coordinated public disclosure | after a fix is shipped, ideally within 90 days of the report |

These targets are best-effort: this is a small project run by maintainers in their spare time.

## Disclosure policy

We follow **coordinated disclosure**:

- We will work with the reporter to understand and reproduce the issue.
- We will keep the report confidential until a fix is released.
- Once a fix is shipped, the issue may be referenced in the changelog and, if appropriate, in a `SECURITY` advisory on GitHub.
- Reporters are credited by name or handle in the advisory unless they prefer to remain anonymous.

## Scope

In scope:

- Authentication and session management (admin login, Portal login, JWT handling).
- Authorisation and permissions (role checks, Portal scope isolation, granular permissions).
- Server-side input validation and SQL/ORM safety.
- Cryptographic operations (Fernet-encrypted secrets in DB, password hashing, JWT signing).
- CSRF, XSS and other classic web vulnerabilities in the Vue frontend or FastAPI backend.
- File handling (uploads, media path validation, Media Manager filesystem operations).
- Dependency vulnerabilities with a credible exploitation path on a default deployment.

Out of scope (unless you can demonstrate concrete impact):

- Self-XSS that requires the victim to paste content into their own console.
- Denial of service against a single self-hosted instance.
- Best-practice findings without a reproducible exploit (e.g. missing security headers behind a properly configured reverse proxy that already sets them).
- Issues in third-party services we integrate with (TMDB, OpenSubtitles, Discord, Imgur). Please report those upstream.
- Vulnerabilities that require physical access to the server.

## Safe-harbour

Good-faith security research is welcomed:

- Test only against your own deployment, never against another user's instance without their written consent.
- Do not access, modify or destroy data that is not yours.
- Do not run automated scans that generate denial-of-service load.
- Stop and report as soon as you have enough evidence to write up the issue.

We will not pursue legal action against researchers who follow this policy.

## Hardening notes

A few defensive choices already documented in the code base:

- Passwords are hashed with bcrypt (cost 12 by default).
- JWT secrets must be ≥ 32 bytes; the application refuses to start otherwise.
- Sensitive settings stored in DB (API keys, webhooks, OAuth tokens) are encrypted at rest with Fernet.
- CSRF protection uses a double-submit cookie pattern on state-changing routes.
- Login attempts are rate-limited and tracked in a dedicated table.

See `ARCHITECTURE.md` for additional details on the auth scopes, encryption-at-rest pipeline and rate-limiting layers.
