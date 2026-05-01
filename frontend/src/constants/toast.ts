/**
 * Toast types consumed by `showToast(message, type)` from
 * `composables/useToast.ts`. Keep values in sync with the `type` prop
 * read by `GlobalToasts.vue` — any new variant must be styled there too.
 */
export const TOAST_TYPE = Object.freeze({
  OK: 'ok',
  ERR: 'err',
  WARN: 'warn',
  MEDIA: 'media',
  INFO: 'info',
} as const)

export type ToastType = (typeof TOAST_TYPE)[keyof typeof TOAST_TYPE]
