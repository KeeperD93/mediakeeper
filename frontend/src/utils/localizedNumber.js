import { getLocale } from '@/i18n'

/**
 * Format a number with the app's active locale (`getLocale`) instead of the
 * browser's, like the date helpers of `datetime.js`: « 12 345 » in French,
 * « 12,345 » in English, whatever language the browser runs in.
 */
export const localizedNumber = (value, options) => value.toLocaleString(getLocale(), options)
