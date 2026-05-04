/**
 * Composable singleton for le module Sous-titres.
 * Centralize shared state: config, quota, profiles, history, Emby libraries.
 */
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'

// ── State singleton (survit au mount/unmount) ──────────────────────────────
const configured = ref(false)
const quota = ref(null)
const profiles = ref([])
const activeProfileId = ref(null)
const embyLibraries = ref([])
const history = ref([])
const historyTotal = ref(0)

const _initialized = ref(false)

// ── Computed ───────────────────────────────────────────────────────────────
const activeProfile = computed(
  () => profiles.value.find(p => p.id === activeProfileId.value) || null,
)

const defaultProfile = computed(() => profiles.value.find(p => p.is_default) || null)

// Mapping ISO 639-2 (3 lettres) → ISO 639-1 (2 lettres) for l'API OpenSubtitles
const LANG_3_TO_2 = {
  fre: 'fr',
  eng: 'en',
  spa: 'es',
  ger: 'de',
  ita: 'it',
  por: 'pt',
  jpn: 'ja',
  chi: 'zh',
  kor: 'ko',
  rus: 'ru',
  ara: 'ar',
  hin: 'hi',
  nld: 'nl',
  pol: 'pl',
  tur: 'tr',
  swe: 'sv',
  dan: 'da',
  nor: 'no',
  fin: 'fi',
  ces: 'cs',
  ron: 'ro',
  hun: 'hu',
  ell: 'el',
  heb: 'he',
  tha: 'th',
  vie: 'vi',
  ind: 'id',
  ukr: 'uk',
}

// Locale UI → langue principale par default (fallback when no profil n'existe)
const LOCALE_DEFAULT_LANG = {
  fr: 'fre',
  en: 'eng',
  es: 'spa',
  de: 'ger',
  it: 'ita',
  pt: 'por',
  ja: 'jpn',
  ko: 'kor',
  zh: 'chi',
  ru: 'rus',
  ar: 'ara',
  nl: 'nld',
  pl: 'pol',
  tr: 'tur',
  sv: 'swe',
}

const defaultLanguages = computed(() => {
  const p = activeProfile.value || defaultProfile.value
  if (p && p.languages && p.languages.length) return p.languages
  // Fallback : langue de l'interface + English
  const locale = localStorage.getItem('mediakeeper_locale') || 'fr'
  const primary = LOCALE_DEFAULT_LANG[locale] || 'eng'
  return primary === 'eng' ? ['eng'] : [primary, 'eng']
})

const defaultLanguagesParam = computed(() => {
  return defaultLanguages.value.map(l => LANG_3_TO_2[l] || l.slice(0, 2)).join(',')
})

const quotaPct = computed(() => {
  if (!quota.value || !quota.value.allowed_downloads) return 0
  return Math.round((quota.value.remaining_downloads / quota.value.allowed_downloads) * 100)
})

const quotaColor = computed(() => {
  if (quotaPct.value > 50) return 'var(--color-success)'
  if (quotaPct.value > 20) return 'var(--color-warning)'
  return 'var(--color-error)'
})

// ── Actions ────────────────────────────────────────────────────────────────

export function useSubtitles() {
  const { apiGet, apiPost, apiPut, apiDelete } = useApi()
  const { t } = useI18n()

  /** Translated un code d'error backend via i18n with fallback au code brut */
  function translateError(code) {
    if (!code) return t('common.error')
    const key = `common.apiError.${code}`
    const translated = t(key)
    return translated === key ? code : translated
  }

  // --- Config & Status ---
  async function loadStatus() {
    try {
      const d = await apiGet('/api/subtitles/status')
      if (d) configured.value = d.configured
    } catch {
      /* silent: status fetch */
    }
  }

  async function loadQuota() {
    if (!configured.value) return
    try {
      const d = await apiGet('/api/subtitles/quota')
      if (d && !d.error) quota.value = d
    } catch {
      /* silent: quota fetch */
    }
  }

  async function loadLibraries() {
    try {
      const d = await apiGet('/api/subtitles/libraries')
      if (Array.isArray(d)) embyLibraries.value = d
    } catch {
      /* silent: libraries fetch */
    }
  }

  // --- Init (calle une seule fois) ---
  async function init() {
    if (_initialized.value) return
    _initialized.value = true
    await loadStatus()
    if (configured.value) loadQuota()
    loadLibraries()
    loadProfiles()
  }

  // --- Profils ---
  async function loadProfiles() {
    try {
      const d = await apiGet('/api/subtitles/profiles')
      if (Array.isArray(d)) {
        profiles.value = d
        // Selectionner le profil par defaut si no n'est actif
        if (!activeProfileId.value) {
          const def = d.find(p => p.is_default)
          if (def) activeProfileId.value = def.id
        }
      }
    } catch {
      /* silent: profiles fetch */
    }
  }

  function setActiveProfile(id) {
    activeProfileId.value = id
  }

  async function createProfile(data) {
    const d = await apiPost('/api/subtitles/profiles', data)
    if (d && d.id) {
      await loadProfiles()
      return d
    }
    return null
  }

  async function updateProfile(id, data) {
    const d = await apiPut(`/api/subtitles/profiles/${id}`, data)
    if (d && d.id) {
      await loadProfiles()
      return d
    }
    return null
  }

  async function deleteProfile(id) {
    await apiDelete(`/api/subtitles/profiles/${id}`)
    if (activeProfileId.value === id) activeProfileId.value = null
    await loadProfiles()
  }

  async function setDefaultProfile(id) {
    await apiPost(`/api/subtitles/profiles/${id}/default`)
    await loadProfiles()
  }

  // --- History ---
  async function loadHistory({ limit = 50, offset = 0, item_id = '', language = '' } = {}) {
    try {
      const params = new URLSearchParams({ limit, offset })
      if (item_id) params.set('item_id', item_id)
      if (language) params.set('language', language)
      const d = await apiGet(`/api/subtitles/history?${params}`)
      if (d && d.items) {
        history.value = d.items
        historyTotal.value = d.total
      }
    } catch {
      /* silent: history fetch */
    }
  }

  async function loadItemHistory(itemId) {
    try {
      return await apiGet(`/api/subtitles/history/${itemId}`)
    } catch {
      return []
    }
  }

  // --- Matrice series ---
  async function loadSeriesMatrix(seriesId, languages = null) {
    const langs = languages || defaultLanguages.value
    const langsParam = langs.join(',')
    try {
      return await apiGet(`/api/subtitles/series-matrix/${seriesId}?languages=${langsParam}`)
    } catch {
      return { series_name: '', seasons: {}, languages: langs, total_episodes: 0, coverage: {} }
    }
  }

  // --- Counter OS available ---
  const _osCountCache = {}

  async function loadAvailableCounts(items) {
    // Filtrer les items deja en cache
    const toFetch = items.filter(i => {
      const key = i.imdb_id || i.tmdb_id
      return key && !(key in _osCountCache)
    })

    if (toFetch.length) {
      try {
        const counts = await apiPost('/api/subtitles/available-count', { items: toFetch })
        if (counts) {
          Object.assign(_osCountCache, counts)
        }
      } catch {
        /* silent: OS count lookup, result falls back to null */
      }
    }

    // Return all counts
    const result = {}
    for (const i of items) {
      const key = i.imdb_id || i.tmdb_id
      if (key && key in _osCountCache) {
        result[key] = _osCountCache[key]
      }
    }
    return result
  }

  function getOsCount(key) {
    return _osCountCache[key] ?? null
  }

  return {
    // State (readonly-ish)
    configured,
    quota,
    profiles,
    activeProfile,
    activeProfileId,
    defaultProfile,
    defaultLanguages,
    defaultLanguagesParam,
    embyLibraries,
    history,
    historyTotal,
    quotaPct,
    quotaColor,

    // Actions
    init,
    loadStatus,
    loadQuota,
    loadLibraries,
    loadProfiles,
    setActiveProfile,
    createProfile,
    updateProfile,
    deleteProfile,
    setDefaultProfile,
    loadHistory,
    loadItemHistory,
    loadSeriesMatrix,
    loadAvailableCounts,
    getOsCount,
    translateError,
  }
}
