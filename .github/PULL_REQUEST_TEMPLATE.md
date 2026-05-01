## Summary

<!-- 1–2 sentences: what this PR does. -->

## Why

<!-- Context / linked bug / ticket. Remove if self-explanatory. -->

## How to test

<!-- Reproducible steps to validate manually. -->

- [ ] Step 1
- [ ] Step 2

## Contributor checklist

See the *Coding conventions checklist* in `CONTRIBUTING.md` for the full list.

- [ ] Mobile-first responsive (project breakpoints, 44 px touch targets, hover-safe).
- [ ] Design tokens used everywhere they exist (no hardcoded colours, radii, font sizes).
- [ ] No `style="..."` inline in templates (unless genuinely runtime-computed).
- [ ] Components stay single-responsibility (presentation in SFC, logic in composables, HTTP only via `useApi`).
- [ ] User-facing strings go through i18n (`$t` / `t()`), FR + EN mirrored.
- [ ] User-facing changelog updated for visible changes (no third-party brand mentioned).
- [ ] File-size convention respected (≤ 300 lines per applicative file).
- [ ] Tests added or updated for critical endpoints / components.
- [ ] `npm run lint`, `npm run typecheck`, `npm run test:unit` pass locally.

## Breaking changes

<!-- If any: list + migration plan. Otherwise: "None". -->

## Screenshots (if UI)

<!-- Before / after. -->
