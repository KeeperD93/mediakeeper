/**
 * Toast types consumed by `showToast(message, type)` from
 * `composables/useToast.ts`. Keep values in sync with the toast list in
 * `App.vue`, which uses the type as a class: style any new variant in
 * `assets/styles/app-shell.css`.
 */
export const TOAST_TYPE = Object.freeze({
  OK: 'ok',
  ERR: 'err',
  WARN: 'warn',
  MEDIA: 'media',
  INFO: 'info',
} as const)

export type ToastType = (typeof TOAST_TYPE)[keyof typeof TOAST_TYPE]
