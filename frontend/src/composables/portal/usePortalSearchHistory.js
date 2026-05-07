import { ref } from 'vue'

const RECENT_KEY = 'mk_portal_recent_searches'
const RECENT_MAX = 5
const RECENT_MAX_LEN = 100

function readStorage() {
  try {
    if (typeof localStorage === 'undefined') return []
    const raw = localStorage.getItem(RECENT_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    const cleaned = []
    const seen = new Set()
    for (const value of parsed) {
      if (typeof value !== 'string') continue
      const trimmed = value.trim()
      if (!trimmed || trimmed.length > RECENT_MAX_LEN) continue
      const lower = trimmed.toLowerCase()
      if (seen.has(lower)) continue
      seen.add(lower)
      cleaned.push(trimmed)
      if (cleaned.length >= RECENT_MAX) break
    }
    return cleaned
  } catch {
    return []
  }
}

function writeStorage(list) {
  try {
    if (typeof localStorage === 'undefined') return
    localStorage.setItem(RECENT_KEY, JSON.stringify(list))
  } catch {
    /* swallow quota / privacy-mode errors */
  }
}

const recents = ref(readStorage())

export function useRecentSearches() {
  function add(value) {
    if (typeof value !== 'string') return
    const trimmed = value.trim()
    if (!trimmed || trimmed.length > RECENT_MAX_LEN) return
    const lower = trimmed.toLowerCase()
    const next = [trimmed, ...recents.value.filter(item => item.toLowerCase() !== lower)].slice(
      0,
      RECENT_MAX,
    )
    recents.value = next
    writeStorage(next)
  }

  function clear() {
    recents.value = []
    try {
      if (typeof localStorage !== 'undefined') localStorage.removeItem(RECENT_KEY)
    } catch {
      /* swallow */
    }
  }

  function reload() {
    recents.value = readStorage()
  }

  return { recents, add, clear, reload }
}

export const __recent_search_constants = {
  RECENT_KEY,
  RECENT_MAX,
  RECENT_MAX_LEN,
}
