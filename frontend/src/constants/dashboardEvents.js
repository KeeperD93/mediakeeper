/**
 * Custom DOM events used to bridge unrelated subtrees on the dashboard
 * page. The global AppTopbar (rendered in the layout) needs to ask
 * the dashboard view (rendered in <router-view>) to enter edit mode when
 * the user taps the "Customize" icon. A module-level event name is
 * cheaper than a Pinia store for a single fire-and-forget signal and
 * avoids duplicating a magic string across consumers.
 */

export const DASHBOARD_EDIT_EVENT = 'mk:dashboard-edit'
