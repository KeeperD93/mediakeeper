import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { resolveApiError, resolveScopedError, useApi } from '@/composables/useApi'
import { useConfirm } from '@/composables/useConfirm'
import { useToast } from '@/composables/useToast'
import {
  BLOCK_REASON,
  SECURITY_ERROR,
  SECURITY_SCOPE,
  UNKNOWN_CLIENT_IP,
} from '@/constants/security'
import { TOAST_TYPE } from '@/constants/toast'
import { localizedDateTime } from '@/utils/datetime'

// Loopback (the server itself) reads as "Local" instead of raw ::1 / 127.x.
const LOOPBACK = new Set(['::1', '127.0.0.1', 'localhost', '::ffff:127.0.0.1'])
// Often enough to see a block appear during an attack, rare enough to stay cheap.
const AUTO_REFRESH_MS = 15000
const ERRORS_SCOPE = 'settings.security.errors'

// One list of the tab: kept on screen once loaded, even when a later reload fails.
function createList(fetchItems) {
  const items = ref([])
  const loaded = ref(false)
  const failed = ref(false)
  let latest = 0
  async function load() {
    // An older answer (a slow refresh, then a newer filter) must not win.
    const request = ++latest
    try {
      const res = await fetchItems()
      if (request !== latest || !res) return
      items.value = res.items || []
      loaded.value = true
      failed.value = false
    } catch (e) {
      if (request === latest) failed.value = true
      throw e
    }
  }
  return { items, loaded, failed, load }
}

export function useParamsSecurity() {
  const { t, te } = useI18n()
  const { apiGet, apiPost, apiDelete } = useApi()
  const { showToast } = useToast()
  const mkConfirm = useConfirm()

  const onlyFailures = ref(true)
  const blockList = createList(() => apiGet('/api/security/blocks'))
  const attemptList = createList(() => {
    const query = new URLSearchParams({
      limit: '100',
      only_failures: onlyFailures.value ? 'true' : 'false',
    })
    return apiGet(`/api/security/attempts?${query}`)
  })
  const busy = ref(false)
  let pendingRefreshes = 0
  let failureShown = false
  let timer = null

  function displayIp(ip) {
    if (!ip) return '—'
    const v = String(ip).trim().toLowerCase()
    if (v === UNKNOWN_CLIENT_IP) return t('settings.security.unknownAddress')
    if (LOOPBACK.has(v) || v.startsWith('127.') || v.startsWith('::ffff:127.')) {
      return t('settings.security.localAddress')
    }
    return ip
  }

  function formatDate(iso) {
    if (!iso) return ''
    return localizedDateTime(new Date(iso))
  }

  function scopeLabel(scope) {
    const key = `settings.security.scopes.${scope}`
    return te(key) ? t(key) : scope
  }

  function reasonLabel(reason) {
    if (!reason) return '—'
    if (reason.startsWith(BLOCK_REASON.AUTO_IP_PREFIX)) return t('settings.security.reasons.autoIp')
    if (reason.startsWith(BLOCK_REASON.AUTO_NAME_PREFIX)) {
      return t('settings.security.reasons.autoName')
    }
    if (reason === BLOCK_REASON.FROM_ATTEMPTS) return t('settings.security.reasons.fromAttempts')
    return reason
  }

  function showFailure(where, e, message) {
    console.error(`[useParamsSecurity.${where}]`, e)
    showToast(message, TOAST_TYPE.ERR)
  }

  async function refresh({ silent = false } = {}) {
    pendingRefreshes++
    const results = await Promise.allSettled([blockList.load(), attemptList.load()])
    pendingRefreshes--
    const failure = results.find(r => r.status === 'rejected')
    if (!failure) {
      failureShown = false
      return
    }
    // A server that stays down would toast every 15 s: a silent refresh says it once.
    if (silent && failureShown) return
    failureShown = true
    const e = failure.reason
    showFailure('refresh', e, resolveApiError(e?.message, 'settings.security.loadFailed'))
  }

  function startAutoRefresh() {
    if (timer) return
    timer = setInterval(() => {
      if (document.hidden || pendingRefreshes > 0 || busy.value) return
      refresh({ silent: true })
    }, AUTO_REFRESH_MS)
  }

  function stopAutoRefresh() {
    clearInterval(timer)
    timer = null
  }

  // Both lists reload after every action: blocking or unblocking also changes what
  // the attempts mean, and the server may have changed more than the clicked row.
  async function runAction(where, request, fallbackKey, doneCode) {
    busy.value = true
    try {
      await request()
      return true
    } catch (e) {
      // Already done elsewhere (another admin, an expiry): the reload shows it.
      if (doneCode && e?.message === doneCode) return true
      showFailure(where, e, resolveScopedError(ERRORS_SCOPE, e?.message, fallbackKey))
      return false
    } finally {
      await refresh()
      busy.value = false
    }
  }

  function addBlock(payload) {
    return runAction(
      'addBlock',
      () => apiPost('/api/security/blocks', payload),
      'settings.security.blockFailed',
    )
  }

  function unblock(block) {
    return runAction(
      'unblock',
      () => apiDelete(`/api/security/blocks/${block.id}`),
      'settings.security.unblockFailed',
      SECURITY_ERROR.BLOCK_NOT_FOUND,
    )
  }

  async function blockAttemptIp(attempt) {
    const scope = attempt.scope || SECURITY_SCOPE.ALL
    const ok = await mkConfirm({
      title: t('settings.security.blockIpConfirmTitle'),
      message: t('settings.security.blockIpConfirmMessage', {
        ip: attempt.ip,
        scope: scopeLabel(scope),
      }),
      variant: 'danger',
      confirmLabel: t('settings.security.blockIp'),
      cancelLabel: t('common.cancel'),
    })
    if (!ok) return false
    return runAction(
      'blockAttemptIp',
      () =>
        apiPost('/api/security/blocks', {
          ip: attempt.ip,
          username: null,
          scope,
          permanent: true,
          reason: BLOCK_REASON.FROM_ATTEMPTS,
        }),
      'settings.security.blockFailed',
    )
  }

  watch(onlyFailures, () => refresh())

  return {
    blocks: blockList.items,
    blocksLoaded: blockList.loaded,
    blocksFailed: blockList.failed,
    attempts: attemptList.items,
    attemptsLoaded: attemptList.loaded,
    attemptsFailed: attemptList.failed,
    onlyFailures,
    busy,
    displayIp,
    formatDate,
    scopeLabel,
    reasonLabel,
    refresh,
    startAutoRefresh,
    stopAutoRefresh,
    addBlock,
    unblock,
    blockAttemptIp,
  }
}
