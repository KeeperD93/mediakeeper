/**
 * Help Center admin operations — CRUD wrapper around
 * /api/portal/admin/help/*. Used inline from the help overlay when the
 * current profile is an admin.
 *
 * Each call goes through ``useApi`` so 401 / network errors flow through
 * the standard portal handler. Lightweight by design: no shared state,
 * each call resolves to the article (or list) returned by the backend.
 */
import { ref } from 'vue'
import { useApi } from '@/composables/useApi'

export function usePortalHelpAdmin() {
  const { apiGet, apiPost, apiPatch, apiPut, apiDelete } = useApi()

  const saving = ref(false)
  const error = ref(null)

  async function run(fn) {
    saving.value = true
    error.value = null
    try {
      return await fn()
    } catch (err) {
      error.value = err?.data?.detail || err?.message || 'help_admin_failed'
      throw err
    } finally {
      saving.value = false
    }
  }

  async function listAdmin({ includeDeleted = false, lang = 'fr' } = {}) {
    return run(async () => {
      const qs = `?include_deleted=${includeDeleted ? 1 : 0}&lang=${encodeURIComponent(lang)}`
      const res = await apiGet(`/api/portal/admin/help/articles${qs}`)
      return Array.isArray(res?.items) ? res.items : []
    })
  }

  async function listTrash({ lang = 'fr' } = {}) {
    return run(async () => {
      const res = await apiGet(`/api/portal/admin/help/trash?lang=${encodeURIComponent(lang)}`)
      return {
        items: Array.isArray(res?.items) ? res.items : [],
        retentionDays: res?.retention_days || 30,
      }
    })
  }

  async function createArticle(payload) {
    return run(() => apiPost('/api/portal/admin/help/articles', payload))
  }

  async function patchMetadata(articleId, patch) {
    return run(() => apiPatch(`/api/portal/admin/help/articles/${articleId}`, patch))
  }

  async function putTranslation(articleId, lang, { title, bodyHtml }) {
    return run(() => apiPut(
      `/api/portal/admin/help/articles/${articleId}/translations/${lang}`,
      { title, body_html: bodyHtml },
    ))
  }

  async function softDelete(articleId) {
    return run(() => apiDelete(`/api/portal/admin/help/articles/${articleId}`))
  }

  async function restore(articleId) {
    return run(() => apiPost(`/api/portal/admin/help/articles/${articleId}/restore`))
  }

  async function hardDelete(articleId) {
    return run(() => apiDelete(`/api/portal/admin/help/articles/${articleId}/hard`))
  }

  async function purge() {
    return run(() => apiPost('/api/portal/admin/help/purge'))
  }

  return {
    saving, error,
    listAdmin, listTrash,
    createArticle, patchMetadata, putTranslation,
    softDelete, restore, hardDelete, purge,
  }
}
