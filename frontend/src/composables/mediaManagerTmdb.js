import { computed } from 'vue'
import {
  apiGet,
  _t,
  subPath,
  checked,
  selectedTmdb,
  tmdbResults,
  tmdbYearQuery,
  currentSeason,
  seasons,
  showSeasonPanel,
  searchType,
  tooltip,
  newNames,
  anomalyRules,
  _autoSearchState,
} from './mediaManagerState'
import { cleanName, extractYear, _levenshtein } from './mediaManagerHelpers'
import { checkedFiles, checkedDirs, _registerAutoSearch } from './mediaManagerNavigation'

function _validYear(y) {
  if (y === null || y === undefined || y === '') return null
  const n = typeof y === 'number' ? y : parseInt(String(y).trim(), 10)
  if (!Number.isInteger(n) || n < 1900 || n > 2099) return null
  return n
}

export const canGenerate = computed(
  () => selectedTmdb.value && (checked.value.size > 0 || searchType.value === 'tv'),
)
export const canRename = computed(() => newNames.value.length > 0)

// ─── TMDB ───
export function setType(t) {
  searchType.value = t
  selectedTmdb.value = null
  tmdbResults.value = []
  showSeasonPanel.value = false
  const q = document.getElementById('tmdb-q-vue')?.value?.trim()
  if (q) doSearch(false, q, _validYear(tmdbYearQuery.value))
}

export async function doSearch(autoSelect = false, query = '', year = null) {
  if (!query?.trim()) return
  tmdbResults.value = []
  selectedTmdb.value = null
  hideTooltip()
  try {
    const ep = searchType.value === 'movie' ? 'movie' : 'tv'
    const lang = anomalyRules.value._tmdbLang || 'fr-FR'
    const validYear = _validYear(year)
    const yearParam = validYear ? `&year=${validYear}` : ''
    const data = await apiGet(
      `/api/media/tmdb/search/${ep}?q=${encodeURIComponent(query)}&language=${encodeURIComponent(lang)}${yearParam}`,
    )
    if (!data?.length) return
    tmdbResults.value = data.slice(0, 10)
    if (autoSelect) pickTMDB(0)
  } catch {
    /* silent: TMDB search miss → empty results panel */
  }
}

export function pickTMDB(idx) {
  const item = tmdbResults.value[idx]
  if (!item) return
  selectedTmdb.value = item
  hideTooltip()
  if (item.type === 'tv') loadSeasons(item.id)
  else {
    showSeasonPanel.value = false
    currentSeason.value = null
  }
}

export async function loadSeasons(tmdbId) {
  showSeasonPanel.value = true
  currentSeason.value = 1
  seasons.value = []
  const lang = anomalyRules.value._tmdbLang || 'fr-FR'
  try {
    const data = await apiGet(
      `/api/media/tmdb/tv/${tmdbId}/seasons?language=${encodeURIComponent(lang)}`,
    )
    if (!Array.isArray(data)) return
    seasons.value = data
    const mPath = subPath.value.match(/[Ss](?:aison\s*)?(\d+)/i)
    if (mPath) currentSeason.value = parseInt(mPath[1])
    else currentSeason.value = data[0]?.number || 1
  } catch {
    /* silent: TMDB seasons unavailable → panel stays empty */
  }
}

export function showTooltipTmdb(item, e) {
  const ov = (item.overview || '').slice(0, 240) + ((item.overview || '').length > 240 ? '…' : '')
  tooltip.value = {
    visible: true,
    title: item.title || '',
    year: item.year || '—',
    vote: item.vote ? item.vote.toFixed(1) : '—',
    overview: ov,
    x: e.clientX + 14,
    y: e.clientY + 14,
  }
}
export function moveTooltip(e) {
  if (!tooltip.value.visible) return
  let x = e.clientX + 14,
    y = e.clientY + 14
  if (x + 250 > window.innerWidth) x = e.clientX - 264
  if (y + 120 > window.innerHeight) y = e.clientY - 134
  tooltip.value.x = x
  tooltip.value.y = y
}
export function hideTooltip() {
  tooltip.value.visible = false
}

// ─── AUTO-SEARCH ───
export function autoSearch(tmdbQueryEl) {
  if (tmdbQueryEl) _autoSearchState.tmdbQueryEl = tmdbQueryEl
  clearTimeout(_autoSearchState.timer)
  _autoSearchState.timer = setTimeout(async () => {
    if (selectedTmdb.value) return
    if (_autoSearchState.dirChangePending) return
    const el = _autoSearchState.tmdbQueryEl
    const cFiles = checkedFiles.value,
      cDirs = checkedDirs.value
    let detected = ''
    let rawSourceName = ''
    // Multi-selection: every checked item must share the same cleaned name —
    // otherwise it's a mixed batch and we'd guess the wrong title.
    const pickConsensus = items => {
      const names = items.map(it => cleanName(it.name)).filter(Boolean)
      if (!names.length) return ''
      const first = names[0]
      return names.every(n => n === first) ? first : ''
    }
    if (cDirs.length > 0) {
      detected = pickConsensus(cDirs)
      if (detected) rawSourceName = cDirs[0]?.name || ''
    } else if (cFiles.length > 0) {
      detected = pickConsensus(cFiles)
      if (detected) rawSourceName = cFiles[0]?.name || ''
    } else if (subPath.value) {
      const segments = subPath.value.split('/').filter(Boolean)
      for (let i = segments.length - 1; i >= 0; i--) {
        const candidate = cleanName(segments[i])
        if (candidate) {
          detected = candidate
          rawSourceName = segments[i]
          break
        }
      }
    }
    if (!detected || !el) return
    el.value = detected
    const detectedYear = extractYear(rawSourceName)
    tmdbYearQuery.value = detectedYear || ''
    await doSearch(true, detected, detectedYear)
  }, 600)
}
_registerAutoSearch(autoSearch)

// ─── FUZZY SEARCH ───
export async function fuzzyTmdbSearch(query, type = 'movie') {
  if (!query?.trim()) return []
  const clean = query.trim().toLowerCase()
  try {
    const lang = anomalyRules.value._tmdbLang || 'fr-FR'
    const ep = type === 'movie' ? 'movie' : 'tv'
    const data = await apiGet(
      `/api/media/tmdb/search/${ep}?q=${encodeURIComponent(query)}&language=${encodeURIComponent(lang)}`,
    )
    if (data?.length) return data.slice(0, 8)
    const words = clean.split(/\s+/).filter(w => w.length > 2)
    if (!words.length) return []
    const fallback = await apiGet(
      `/api/media/tmdb/search/${ep}?q=${encodeURIComponent(words[0])}&language=${encodeURIComponent(lang)}`,
    )
    if (!fallback?.length) return []
    return fallback
      .map(r => ({ ...r, _dist: _levenshtein(clean, (r.title || r.name || '').toLowerCase()) }))
      .sort((a, b) => a._dist - b._dist)
      .slice(0, 6)
  } catch {
    return []
  }
}
