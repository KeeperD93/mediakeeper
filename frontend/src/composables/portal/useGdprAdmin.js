/**
 * GDPR opt-in admin operations — wrapper around
 * /api/portal/admin/gdpr/* and the deletion-request admin surface.
 *
 * Mirrors the lightweight style of ``usePortalHelpAdmin``: each call
 * resolves to the backend payload, errors flow through ``useApi``.
 */
import { ref } from 'vue'
import { useApi } from '@/composables/useApi'

const DEFAULT_SETTINGS = {
  enabled: false,
  privacy_text_fr: '',
  privacy_text_en: '',
  dpo_contact: '',
  account_purge_delay_days: 30,
}

export function useGdprAdmin() {
  const { apiGet, apiPut, apiDelete } = useApi()
  const saving = ref(false)
  const error = ref(null)

  async function run(fn) {
    saving.value = true
    error.value = null
    try {
      return await fn()
    } catch (err) {
      error.value = err?.data?.detail || err?.message || 'gdpr_admin_failed'
      throw err
    } finally {
      saving.value = false
    }
  }

  async function fetchSettings() {
    return run(async () => {
      const res = await apiGet('/api/portal/admin/gdpr/settings')
      return { ...DEFAULT_SETTINGS, ...(res || {}) }
    })
  }

  async function saveSettings(patch) {
    // Drop undefined keys so we never overwrite a value the user has
    // not touched in this commit.
    const body = {}
    for (const [k, v] of Object.entries(patch)) {
      if (v !== undefined) body[k] = v
    }
    return run(async () => {
      const res = await apiPut('/api/portal/admin/gdpr/settings', body)
      return { ...DEFAULT_SETTINGS, ...(res || {}) }
    })
  }

  async function fetchPendingDeletions() {
    return run(async () => {
      const res = await apiGet(
        '/api/portal/admin/users?pending_deletion=true&limit=200',
      )
      return Array.isArray(res?.items) ? res.items : []
    })
  }

  async function cancelDeletionRequest(profileId) {
    return run(() => apiDelete(
      `/api/portal/admin/users/${profileId}/deletion-request`,
    ))
  }

  return {
    saving, error,
    fetchSettings, saveSettings,
    fetchPendingDeletions, cancelDeletionRequest,
  }
}

export { DEFAULT_SETTINGS }
