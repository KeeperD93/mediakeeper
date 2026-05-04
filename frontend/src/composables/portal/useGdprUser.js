/**
 * GDPR opt-in user-side operations — wrapper around
 * /api/portal/me/* GDPR endpoints.
 *
 * Mirrors ``useGdprAdmin`` but exposes the user-facing surface:
 * privacy-text fetch, ZIP export download, deletion-request submit
 * and cancel.
 *
 * The export call cannot route through ``useApi`` because it parses
 * a binary blob and the ``Content-Disposition`` filename — useApi
 * auto-calls ``res.json()`` on success and would throw on a ZIP body.
 */
import { fetchApiResponse } from '@/composables/apiClient'
import { useApi } from '@/composables/useApi'

export const EXPORT_LIMIT = 'export_rate_limited'
export const EXPORT_TOO_LARGE = 'export_too_large'

function parseFilename(disposition) {
  // Match the simple ``filename="…"`` form the backend uses; falls
  // back to a sensible default so the download always succeeds.
  if (!disposition) return 'mediakeeper-export.zip'
  const match = /filename\s*=\s*"?([^";]+)"?/i.exec(disposition)
  return (match && match[1]) || 'mediakeeper-export.zip'
}

function triggerBlobDownload(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  // Defer revoke so Safari has time to start the download.
  setTimeout(() => URL.revokeObjectURL(url), 5000)
}

export function useGdprUser() {
  const { apiGet, apiPost, apiDelete } = useApi()

  async function getPrivacyText(lang) {
    const qs = lang ? `?lang=${encodeURIComponent(lang)}` : ''
    return apiGet(`/api/portal/me/privacy-text${qs}`)
  }

  async function exportMyData() {
    const res = await fetchApiResponse('/api/portal/me/export', {
      method: 'GET',
      retryOn401: true,
      redirectOn401: false,
    })
    if (!res) {
      throw new Error('export_unavailable')
    }
    if (res.status === 429) {
      // Surface the Retry-After hint so the caller can localise the
      // toast (epoch seconds OR HTTP-date OR missing). The component
      // formats whichever it gets.
      const retryAfter = res.headers.get('retry-after') || ''
      const err = new Error(EXPORT_LIMIT)
      err.code = EXPORT_LIMIT
      err.retryAfter = retryAfter
      throw err
    }
    if (res.status === 413) {
      const err = new Error(EXPORT_TOO_LARGE)
      err.code = EXPORT_TOO_LARGE
      throw err
    }
    if (!res.ok) {
      throw new Error(`export_failed_${res.status}`)
    }
    const blob = await res.blob()
    const filename = parseFilename(res.headers.get('content-disposition'))
    triggerBlobDownload(blob, filename)
    return { filename }
  }

  async function submitDeletion() {
    // POST returns 200 with the new schedule, OR 409 ``already_pending``
    // with the existing schedule embedded in the detail. Both are
    // success-shaped from the UI's standpoint: we want the banner to
    // appear with whichever ``pending_deletion_at`` the backend has.
    try {
      const data = await apiPost('/api/portal/me/deletion-request')
      return { ok: true, data, alreadyPending: false }
    } catch (err) {
      // useApi throws ``new Error(detail)``. The 409 ``detail`` is an
      // object with ``code/deletion_requested_at/pending_deletion_at``;
      // we surface that to the caller so it can refresh /me without a
      // separate failure path.
      const message = err?.message || ''
      if (message.includes('already_pending')) {
        return { ok: true, alreadyPending: true }
      }
      throw err
    }
  }

  async function cancelDeletion() {
    return apiDelete('/api/portal/me/deletion-request')
  }

  return {
    getPrivacyText,
    exportMyData,
    submitDeletion,
    cancelDeletion,
  }
}
