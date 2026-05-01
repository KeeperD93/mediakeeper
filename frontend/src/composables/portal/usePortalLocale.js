/**
 * usePortalLocale
 * ----------------
 * Manages the Portal-specific UI language independently of the global
 * MediaKeeper locale preference.
 *
 * Behaviour:
 * - When the user enters the Portal, we read profile.language and apply it
 *   ephemerally (without touching the global mediakeeper_locale in localStorage).
 * - When the user leaves the Portal, we restore the previously saved global
 *   MediaKeeper locale.
 *
 * Rationale: Emby-only users (non-admin) cannot reach the MediaKeeper admin
 * UI, so they need an in-Portal way to pick their UI/trailer language without
 * polluting the global preference of an admin who might share the device.
 */
import { applyLocaleEphemeral, getLocale, isSupportedLocale } from '@/i18n'

let savedGlobalLocale = null

export function usePortalLocale() {
  /**
   * Apply a Portal profile's preferred language to the running i18n
   * instance, saving the previous (global) value so it can be restored later.
   */
  function applyPortalLocale(language) {
    if (!language || !isSupportedLocale(language)) return
    if (savedGlobalLocale === null) {
      // Only save once on first entry, to handle nested route changes
      // inside the Portal without losing the original global locale.
      savedGlobalLocale = getLocale()
    }
    applyLocaleEphemeral(language)
  }

  /**
   * Restore the global MediaKeeper locale that was active before entering
   * the Portal. Safe to call even if no override was applied.
   */
  function restoreGlobalLocale() {
    if (savedGlobalLocale && isSupportedLocale(savedGlobalLocale)) {
      applyLocaleEphemeral(savedGlobalLocale)
    }
    savedGlobalLocale = null
  }

  return { applyPortalLocale, restoreGlobalLocale }
}
