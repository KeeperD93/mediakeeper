import { createI18n } from 'vue-i18n'
import fr from '@/locales/fr.json'
import en from '@/locales/en.json'
import { fetchApiResponse } from '@/composables/apiClient'

/**
 * Available locales for the language switcher.
 * Only fully translated locales are exposed in production UI.
 */
export const AVAILABLE_LOCALES = [
  { code: 'fr', label: 'Français', flag: '🇫🇷' },
  { code: 'en', label: 'English', flag: '🇬🇧' },
]

const SUPPORTED_CODES = AVAILABLE_LOCALES.map((l) => l.code)
const LOCALE_LOADERS = {}
const loadedLocales = new Set(['fr', 'en'])
const initialLocale = detectLocale()
let localeRequestId = 0

// Detect initial locale: localStorage > navigator > 'fr'
function detectLocale() {
  const saved = localStorage.getItem('mediakeeper_locale')
  if (saved && SUPPORTED_CODES.includes(saved)) return saved

  const nav = navigator.language?.split('-')[0]
  if (nav && SUPPORTED_CODES.includes(nav)) return nav
  return 'fr' // default
}

const i18n = createI18n({
  legacy: false, // Composition API mode
  locale: initialLocale,
  fallbackLocale: 'en',
  messages: { fr, en },
  // Surface missing/fallback warnings in dev only; silent in production builds
  missingWarn: import.meta.env.DEV,
  fallbackWarn: import.meta.env.DEV,
})

document.documentElement.lang = i18n.global.locale.value

export default i18n

async function ensureLocaleMessages(locale) {
  if (loadedLocales.has(locale)) return true
  const loader = LOCALE_LOADERS[locale]
  if (!loader) return false
  const module = await loader()
  i18n.global.setLocaleMessage(locale, module.default || module)
  loadedLocales.add(locale)
  return true
}

async function switchLocale(locale, { persist = false } = {}) {
  if (!SUPPORTED_CODES.includes(locale)) return false
  const requestId = ++localeRequestId
  const available = await ensureLocaleMessages(locale)
  if (!available || requestId !== localeRequestId) return false
  i18n.global.locale.value = locale
  if (persist) {
    localStorage.setItem('mediakeeper_locale', locale)
    syncLocaleToServer(locale)
  }
  document.documentElement.lang = locale
  return true
}

async function syncLocaleToServer(locale) {
  try {
    await fetchApiResponse('/api/auth/locale', {
      method: 'POST',
      body: JSON.stringify({ locale }),
      retryOn401: false,
      redirectOn401: false,
    })
  } catch { /* silent: locale sync is best-effort, UI already switched */ }
}

export async function initializeLocale() {
  await switchLocale(initialLocale)
}

/**
 * Set locale and persist to localStorage (global MediaKeeper preference).
 * Can be called from useTheme or a language switcher.
 */
export function setLocale(locale) {
  return switchLocale(locale, { persist: true })
}

/**
 * Get current locale.
 */
export function getLocale() {
  return i18n.global.locale.value
}

/**
 * Apply a locale WITHOUT persisting to global storage.
 * Used by the Portal to override the UI language scoped to its own session,
 * while keeping the user's global MediaKeeper preference untouched.
 */
export function applyLocaleEphemeral(locale) {
  return switchLocale(locale)
}

/**
 * Check if a locale code is supported.
 */
export function isSupportedLocale(code) {
  return SUPPORTED_CODES.includes(code)
}
