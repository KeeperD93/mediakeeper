# Security policy

<p align="center">
  <b>English</b> · <a href="SECURITY-fr.md">Français</a>
</p>

## Reporting a vulnerability

**Please do not open a public issue for security problems.**

The preferred channel is **GitHub Private vulnerability reporting** (Security tab → "Report a vulnerability"). Reports stay private until coordinated disclosure.

If for any reason you cannot reach the Private vulnerability reporting form, open a brief, non-revealing public issue asking for a private channel and a maintainer will reply with one. **Do not include exploit details in that initial issue.**

When reporting, please include:

- A clear description of the issue
- The affected version (commit hash if possible)
- Steps to reproduce
- The expected impact and any proof of concept
- Whether you would like to be credited in the eventual advisory

---

## Supported versions

| Version | Supported |
|---|---|
| `0.9.x` (current) | ✅ Latest minor only |
| `< 0.9` | ❌ Please upgrade before reporting |

Until `1.0.0` ships, **only the latest `0.9.x` minor receives security fixes**. After `1.0.0`, the same policy applies: the latest stable line is the only supported one.

---

## What to expect

| Stage | Target |
|---|---|
| Acknowledgement of receipt | within 72 hours |
| Initial triage / severity assessment | within 7 days |
| Fix or mitigation plan communicated | within 30 days for confirmed issues |
| Coordinated public disclosure | after a fix ships, ideally within 90 days |

These targets are best-effort: this is a small project run by a maintainer in their spare time.

---

## Scope

**In scope:**

- Authentication and session management (admin login, Portal login, JWT handling)
- Authorisation and permissions (scope isolation, granular permissions)
- Server-side input validation and SQL/ORM safety
- Cryptography (Fernet-encrypted secrets in DB, password hashing, JWT signing)
- CSRF, XSS and other classic web vulnerabilities in the frontend or backend
- File handling (uploads, media path validation, Media Manager filesystem operations)
- Dependency vulnerabilities with a credible exploitation path on a default deployment

**Out of scope (unless you can demonstrate concrete impact):**

- Self-XSS requiring the victim to paste content into their own console
- Denial-of-service against a single self-hosted instance
- Best-practice findings without a reproducible exploit
- Issues in upstream third-party services — please report those upstream
- Vulnerabilities requiring physical access to the server

---

## Safe harbour

Good-faith security research is welcomed:

- Test only against your own deployment, never against another user's instance without their written consent
- Do not access, modify or destroy data that is not yours
- Do not run automated scans that generate denial-of-service load
- Stop and report as soon as you have enough evidence to write up the issue

We will not pursue legal action against researchers who follow this policy.

---

## Disclosure policy

We follow **coordinated disclosure**: we will work with the reporter to understand and reproduce the issue, keep the report confidential until a fix is released, and credit the reporter in the advisory unless they prefer to remain anonymous.

---

## Hardening notes

A few defensive choices already documented in the code base:

- Passwords are hashed with bcrypt (cost factor 12 by default).
- JWT secrets must be ≥ 32 bytes; the application refuses to start otherwise.
- Sensitive settings stored in the database (API keys, webhooks, OAuth tokens) are encrypted at rest with Fernet.
- CSRF protection uses a double-submit cookie pattern on every state-changing route.
- Login attempts are rate-limited and tracked in a dedicated table.
- A dedicated `Security` workflow runs `pip-audit`, `npm audit`, `bandit`, `ruff S` and `semgrep` on every push and weekly.
