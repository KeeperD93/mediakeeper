// Localise ISO language and country codes through the native Intl
// DisplayNames API. TMDB only translates a subset of these labels, so we
// resolve them client-side from the raw codes returned by the backend.
const LANGUAGE_NAMES_CACHE = new Map()
const REGION_NAMES_CACHE = new Map()

function getLanguageNames(locale) {
  if (!LANGUAGE_NAMES_CACHE.has(locale)) {
    LANGUAGE_NAMES_CACHE.set(
      locale,
      new Intl.DisplayNames([locale], { type: 'language', fallback: 'code' }),
    )
  }
  return LANGUAGE_NAMES_CACHE.get(locale)
}

function getRegionNames(locale) {
  if (!REGION_NAMES_CACHE.has(locale)) {
    REGION_NAMES_CACHE.set(
      locale,
      new Intl.DisplayNames([locale], { type: 'region', fallback: 'code' }),
    )
  }
  return REGION_NAMES_CACHE.get(locale)
}

export function formatLanguage(code, locale) {
  if (!code) return ''
  try {
    return getLanguageNames(locale).of(String(code).toLowerCase()) || ''
  } catch {
    return String(code).toUpperCase()
  }
}

export function formatCountry(code, locale) {
  if (!code) return ''
  try {
    return getRegionNames(locale).of(String(code).toUpperCase()) || ''
  } catch {
    return String(code).toUpperCase()
  }
}
