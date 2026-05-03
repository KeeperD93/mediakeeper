import { ref } from 'vue'
import { fetchApiResponse } from './apiClient'

const status = ref(null)
let inflight = null

export function useEncryptionKeyStatus() {
  async function refresh() {
    if (inflight) return inflight
    inflight = (async () => {
      try {
        const res = await fetchApiResponse('/api/health/encryption', {
          retryOn401: false,
          redirectOn401: false,
        })
        if (res && res.ok) {
          status.value = await res.json()
        }
      } catch {
        // Silent: a transient failure must not block admin pages.
      } finally {
        inflight = null
      }
    })()
    return inflight
  }

  return { status, refresh }
}
