/**
 * Custom DOM events used to bridge unrelated subtrees on the dashboard
 * page. The global AppTopbar (rendered in the layout) needs to ask
 * MobileDashboard (rendered in <router-view>) to enter edit mode when
 * the user taps the "Customize" icon. A module-level event name is
 * cheaper than a Pinia store for a single fire-and-forget signal and
 * satisfies Rules.md §6 — no magic string repeated across consumers.
 */

export const MOBILE_EDIT_EVENT = 'mk:dashboard-mobile-edit'
