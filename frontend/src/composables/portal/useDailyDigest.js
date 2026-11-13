import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { usePortalNews } from '@/composables/portal/usePortalNews'
import { TOAST_TYPE } from '@/constants/toast'

const DIGEST_URL = '/api/portal/daily-digest'
const CHANGELOG_SEEN_URL = '/api/portal/changelog/seen'

/**
 * Data of the daily digest window: the digest, whether it was closed today, the
 * view the account keeps (full or compact), and what the window learns about the
 * news and the new Portal version it shows.
 */
export function useDailyDigest() {
  const { apiGet, apiPost, apiPut } = useApi()
  const { markRead } = usePortalNews()
  const { showToast } = useToast()
  const { t } = useI18n()

  const digest = ref(null)
  const dismissed = ref(false)
  const compact = ref(false)
  const loading = ref(false)
  const error = ref(false)
  // News whose whole text the window showed without « Read more »: read on close.
  const seenNews = new Set()
  let viewRequest = 0

  async function load({ force = false } = {}) {
    loading.value = true
    error.value = false
    const viewRequestAtStart = viewRequest
    try {
      const data = await apiGet(force ? `${DIGEST_URL}?force=true` : DIGEST_URL)
      dismissed.value = !!data?.dismissed
      // A switch made while loading wins over the view the answer remembers.
      if (viewRequest === viewRequestAtStart) compact.value = !!data?.compact
      digest.value = data?.digest || null
      seenNews.clear()
      return true
    } catch {
      error.value = true
      return false
    } finally {
      loading.value = false
    }
  }

  /** Shown for the day: the window waits for tomorrow before opening by itself. */
  async function dismiss() {
    readSeenNews()
    try {
      await apiPost(`${DIGEST_URL}/dismiss`, {})
    } catch {
      /* best effort: the window still closes */
    }
  }

  /** The view switches at once; a refused save puts the previous one back. */
  async function setCompact(value) {
    const previous = compact.value
    const request = ++viewRequest
    compact.value = value
    try {
      await apiPut(`${DIGEST_URL}/view`, { compact: value })
    } catch {
      if (request !== viewRequest) return
      compact.value = previous
      showToast(t('portal.dailyDigest.viewError'), TOAST_TYPE.ERR)
    }
  }

  function findNews(id) {
    return digest.value?.news?.find(item => item.id === id)
  }

  function sendRead(item) {
    item.is_new = false
    markRead(item.id, true).catch(() => {})
  }

  /** The viewer opened the whole text: the « New » mark goes at once. */
  function readNews(id) {
    const item = findNews(id)
    seenNews.delete(id)
    if (item?.is_new) sendRead(item)
  }

  function noteNewsSeen(id) {
    if (findNews(id)?.is_new) seenNews.add(id)
  }

  function readSeenNews() {
    for (const id of seenNews) {
      const item = findNews(id)
      if (item?.is_new) sendRead(item)
    }
    seenNews.clear()
  }

  /** The viewer opened the new version's changes: the « New » mark goes at once. */
  function openRelease() {
    const release = digest.value?.release
    if (!release?.is_new) return
    release.is_new = false
    apiPost(CHANGELOG_SEEN_URL, { version: release.version }).catch(() => {})
  }

  return {
    digest,
    dismissed,
    compact,
    loading,
    error,
    load,
    dismiss,
    setCompact,
    readNews,
    noteNewsSeen,
    openRelease,
  }
}
