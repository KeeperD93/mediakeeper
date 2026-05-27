/* Stat card accent colors — centralised so the dashboard widgets don't
 * hardcode hex strings at the call site. Each entry maps a stat id to
 * the hex consumed by ``<StatCard :accent="...">``.
 *
 * Why a TS constant instead of CSS tokens:
 *   StatCard.vue runs hex-string math at runtime (``hexToRgba`` for the
 *   ambient glow), so a CSS variable would force a JS resolver on every
 *   render. Centralising the four hexes here keeps the call site clean
 *   and the runtime simple — the canonical pattern for shared
 *   identifiers consumed at ≥ 2 call sites.
 *
 * Visual reference: catalogued in Storybook under
 * "Design system → Design tokens → Module colours" — the four hexes
 * are picked from the same palette family.
 */
export const STAT_CARD_ACCENT = Object.freeze({
  plays: '#6366f1' /* indigo — Tailwind 500 */,
  duration: '#10b981' /* emerald — Tailwind 500 */,
  duplicates: '#f43f5e' /* rose — Tailwind 500, matches --color-module-duplicates */,
  storage: '#f59e0b' /* amber — Tailwind 500 */,
  watchlist: '#8b5cf6' /* purple — matches --color-module-watchlist */,
} as const)

export type StatCardAccentKey = keyof typeof STAT_CARD_ACCENT

/* Binary alert state used by the value/hover tint on stat cards that
 * expose a positive/negative score (duplicates count, missing episodes,
 * health score). Hex strings (not ``var(--token)``) because the prop
 * is consumed both by CSS color-mix and by the JS ``hexToRgba`` helper
 * in StatCard — nested ``var()`` inside ``color-mix`` doesn't resolve
 * reliably across browsers. The Tailwind-500 hexes match the
 * saturation of ``STAT_CARD_ACCENT`` accents (storage #f59e0b amber-500,
 * duplicates #f43f5e rose-500, etc.) so the hover halo reads at the
 * same visual intensity. Tailwind-400 (the ``--color-success`` /
 * ``--color-error`` tokens used for badges) was too desaturated for
 * the hover glow. */
export const STAT_STATE_COLOR = Object.freeze({
  ok: '#22c55e' /* Tailwind green-500, mirrors --color-module-stats */,
  alert: '#ef4444' /* Tailwind red-500, mirrors --color-error-strong */,
} as const)
