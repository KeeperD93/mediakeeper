import { ref, reactive, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'
import { useToast } from '@/composables/useToast'
import { TOAST_TYPE } from '@/constants/toast'
import { TASK_STATUS } from '@/constants/scheduler'
import { useConfirm } from '@/composables/useConfirm'

export function useNotifs() {
  const { t } = useI18n()
  const { apiGet, apiFetch } = useApi()
  const { showToast } = useToast()
  const mkConfirm = useConfirm()

  const saving = ref(false)
  const testing = ref(null)
  const histFilter = ref('')
  const history = ref([])
  const hStats = reactive({ total: 0, sent: 0, failed: 0 })

  const discord = reactive({ enabled: false, delay: 10, image_host: 'imgur', webhooks: [] })
  const imgur = reactive({
    client_id: '',
    client_secret: '',
    client_secret_configured: false,
    client_secret_length: 0,
  })
  const rules = reactive({
    dnd_enabled: false,
    dnd_start: '23:00',
    dnd_end: '07:00',
    library_filter: [],
    min_resolution: '',
    genre_filter: [],
  })

  const libraryFilterText = computed({
    get: () => rules.library_filter.join(', '),
    set: v => {
      rules.library_filter = v
        .split(',')
        .map(s => s.trim())
        .filter(Boolean)
    },
  })
  const genreFilterText = computed({
    get: () => rules.genre_filter.join(', '),
    set: v => {
      rules.genre_filter = v
        .split(',')
        .map(s => s.trim())
        .filter(Boolean)
    },
  })

  const filteredHistory = computed(() => {
    if (!histFilter.value) return history.value
    return history.value.filter(h => h.status === histFilter.value)
  })

  function whHealth(wh) {
    if (!wh.enabled) return 'health-off'
    if (!wh.url && !wh.url_configured) return 'health-err'
    const fails = history.value.filter(
      h => h.webhook_name === wh.name && h.status === TASK_STATUS.FAILED,
    ).length
    if (fails > 2) return 'health-err'
    if (fails > 0) return 'health-warn'
    return 'health-ok'
  }
  function whHealthTip(wh) {
    const h = whHealth(wh)
    if (h === 'health-off') return t('notifications.discord.healthOff')
    if (h === 'health-err') return t('notifications.discord.healthErr')
    if (h === 'health-warn') return t('notifications.discord.healthWarn')
    return 'OK'
  }

  function addWebhook() {
    discord.webhooks.push({
      id: Date.now().toString(),
      name: t('notifications.discord.newWebhookName'),
      url: '',
      url_configured: false,
      enabled: true,
      _open: true,
      templates: {},
      settings: {},
      events: {
        added: true,
        offline: false,
        duplicate: false,
        new_request: false,
        request_approved: false,
        request_available: false,
        request_rejected: false,
        partially_available: false,
        new_issue: false,
        issue_comment: false,
        issue_resolved: false,
        emby_alerts: false,
      },
    })
  }

  async function testWh(idx, type) {
    const wh = discord.webhooks[idx]
    const hasStoredUrl = !!(wh.url || wh.url_configured)
    if (!hasStoredUrl) {
      showToast(t('notifications.discord.invalidUrl'), TOAST_TYPE.ERR)
      return
    }
    if (
      wh.url &&
      !wh.url.startsWith('https://discord.com/api/webhooks/') &&
      !wh.url.startsWith('https://discordapp.com/api/webhooks/')
    ) {
      showToast(t('notifications.discord.invalidUrl'), TOAST_TYPE.ERR)
      return
    }
    testing.value = 'tpl' + type
    try {
      const res = await apiFetch('/api/notifications/discord/test', {
        method: 'POST',
        body: JSON.stringify({
          webhook_url: wh.url || '',
          webhook_id: wh.id,
          wh_config: {
            templates: wh.templates || {},
            settings: wh.settings || {},
            image_host: discord.image_host,
          },
          test_type: type,
        }),
      })
      if (res?.ok) showToast(t('notifications.discord.testSent'), TOAST_TYPE.OK)
      else showToast(t('notifications.discord.testError'), TOAST_TYPE.ERR)
    } catch {
      showToast(t('common.error'), TOAST_TYPE.ERR)
    }
    testing.value = null
  }

  async function saveDiscord() {
    saving.value = true
    try {
      const res = await apiFetch('/api/notifications/discord/config', {
        method: 'POST',
        body: JSON.stringify({
          enabled: discord.enabled,
          delay: discord.delay,
          image_host: discord.image_host,
          // Strip the UI-only accordion flag: the backend WebhookItem schema is
          // extra="forbid" and rejects an unknown `_open` field with a 422.
          webhooks: discord.webhooks.map(({ _open, ...wh }) => wh),
        }),
      })
      if (res?.ok) {
        await loadDiscordConfig()
        showToast(t('notifications.discord.saved'), TOAST_TYPE.OK)
      } else showToast(t('common.error'), TOAST_TYPE.ERR)
    } catch {
      showToast(t('common.error'), TOAST_TYPE.ERR)
    }
    saving.value = false
  }

  async function saveImgur() {
    try {
      const res = await apiFetch('/api/notifications/imgur/config', {
        method: 'POST',
        body: JSON.stringify({
          client_id: imgur.client_id,
          client_secret: imgur.client_secret,
          client_secret_configured: imgur.client_secret_configured,
        }),
      })
      if (res?.ok) {
        await loadImgurConfig()
        showToast(t('notifications.imgur.saved'), TOAST_TYPE.OK)
      } else showToast(t('common.error'), TOAST_TYPE.ERR)
    } catch {
      showToast(t('common.error'), TOAST_TYPE.ERR)
    }
  }

  async function saveRules() {
    try {
      const res = await apiFetch('/api/notifications/rules', {
        method: 'POST',
        body: JSON.stringify(rules),
      })
      if (res?.ok) showToast(t('notifications.discord.rulesSaved'), TOAST_TYPE.OK)
      else showToast(t('common.error'), TOAST_TYPE.ERR)
    } catch {
      showToast(t('common.error'), TOAST_TYPE.ERR)
    }
  }

  async function clearHistory() {
    const ok = await mkConfirm({
      title: t('common.confirmTitle.clearHistory'),
      message: t('notifications.discord.clearHistoryConfirm'),
      variant: 'danger',
    })
    if (!ok) return
    try {
      await apiFetch('/api/notifications/history', { method: 'DELETE' })
      history.value = []
      hStats.total = 0
      hStats.sent = 0
      hStats.failed = 0
      showToast(t('notifications.discord.historyCleared'), TOAST_TYPE.OK)
    } catch (e) {
      console.error('[useNotifs.clearHistory] failed to clear history', e)
      showToast(t('common.apiError.deleteFailed'), TOAST_TYPE.ERR)
    }
  }

  function fmtDate(d) {
    if (!d) return ''
    return new Date(d).toLocaleDateString(undefined, {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  async function loadDiscordConfig() {
    const d = await apiGet('/api/notifications/discord/config')
    if (!d) return
    discord.enabled = d.enabled || false
    discord.delay = d.delay ?? 10
    discord.image_host = d.image_host || 'imgur'
    discord.webhooks = (d.webhooks || []).map(w => ({
      ...w,
      url: w.url || '',
      url_configured: !!w.url_configured,
      templates: w.templates || {},
      settings: w.settings || {},
      _open: false,
    }))
  }

  async function loadImgurConfig() {
    const d = await apiGet('/api/notifications/imgur/config')
    if (!d) return
    imgur.client_id = d.client_id || ''
    imgur.client_secret = d.client_secret || ''
    imgur.client_secret_configured = !!d.client_secret_configured
    imgur.client_secret_length = Number(d.client_secret_length) || 0
  }

  onMounted(async () => {
    try {
      await loadDiscordConfig()
    } catch {
      /* silent: config load, UI stays on defaults */
    }
    try {
      await loadImgurConfig()
    } catch {
      /* silent: config load, UI stays on defaults */
    }
    try {
      const d = await apiGet('/api/notifications/rules')
      if (d) Object.assign(rules, d)
    } catch {
      /* silent: rules fetch */
    }
    try {
      const d = await apiGet('/api/notifications/history')
      if (d && d.items) history.value = d.items
      else if (Array.isArray(d)) history.value = d
    } catch {
      /* silent: history fetch */
    }
    try {
      const d = await apiGet('/api/notifications/history/stats')
      if (d) Object.assign(hStats, d)
    } catch {
      /* silent: stats fetch */
    }
  })

  return {
    saving,
    testing,
    histFilter,
    history,
    hStats,
    discord,
    imgur,
    rules,
    libraryFilterText,
    genreFilterText,
    filteredHistory,
    whHealth,
    whHealthTip,
    addWebhook,
    testWh,
    saveDiscord,
    saveImgur,
    saveRules,
    clearHistory,
    fmtDate,
  }
}
