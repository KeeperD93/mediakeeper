import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { localizedDateTime } from '@/utils/datetime'

// Loopback (the server itself) reads as "Local" instead of raw ::1 / 127.x.
const LOOPBACK = new Set(['::1', '127.0.0.1', 'localhost', '::ffff:127.0.0.1'])

export function useParamsSecurity() {
  const { t } = useI18n()
  const { apiGet, apiPost, apiDelete } = useApi()

  const blocks = ref([])
  const attempts = ref([])
  const loadingBlocks = ref(false)
  const loadingAttempts = ref(false)
  const onlyFailures = ref(true)

  function displayIp(ip) {
    if (!ip) return '—'
    const v = String(ip).trim().toLowerCase()
    if (LOOPBACK.has(v) || v.startsWith('127.') || v.startsWith('::ffff:127.')) {
      return t('settings.security.localAddress')
    }
    return ip
  }

  function formatDate(iso) {
    if (!iso) return ''
    return localizedDateTime(new Date(iso))
  }

  async function loadBlocks() {
    loadingBlocks.value = true
    try {
      const res = await apiGet('/api/security/blocks')
      blocks.value = res?.items || []
    } finally {
      loadingBlocks.value = false
    }
  }

  async function loadAttempts() {
    loadingAttempts.value = true
    try {
      const query = new URLSearchParams({
        limit: '100',
        only_failures: onlyFailures.value ? 'true' : 'false',
      })
      const res = await apiGet(`/api/security/attempts?${query}`)
      attempts.value = res?.items || []
    } finally {
      loadingAttempts.value = false
    }
  }

  async function addBlock(payload) {
    await apiPost('/api/security/blocks', payload)
  }

  async function removeBlock(id) {
    await apiDelete(`/api/security/blocks/${id}`)
    await loadBlocks()
  }

  async function quickBlockIp(attempt) {
    await apiPost('/api/security/blocks', {
      ip: attempt.ip,
      username: null,
      scope: attempt.scope || 'all',
      permanent: true,
      reason: 'manual_from_attempts',
    })
    await loadBlocks()
  }

  return {
    blocks,
    attempts,
    loadingBlocks,
    loadingAttempts,
    onlyFailures,
    displayIp,
    formatDate,
    loadBlocks,
    loadAttempts,
    addBlock,
    removeBlock,
    quickBlockIp,
  }
}
