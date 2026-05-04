import { useApi } from '@/composables/useApi'

const cache = {}
const inflight = {}
const CACHE_TTL = 7 * 24 * 3600 * 1000

/**
 * Charge et cache les images de profil users Emby.
 * Use /api/emby/user-image/{userId} (cookie httpOnly).
 */
export function useUserImages() {
  const { apiFetch } = useApi()

  async function getUserImageUrl(userId) {
    if (!userId) return null

    const cached = cache[userId]
    if (cached && Date.now() - cached.ts < CACHE_TTL) return cached.url
    if (inflight[userId]) return inflight[userId]

    inflight[userId] = (async () => {
      try {
        const res = await apiFetch(`/api/emby/user-image/${userId}`)
        if (!res || res.status === 204) {
          cache[userId] = { url: null, ts: Date.now() }
          return null
        }
        if (res.ok) {
          const blob = await res.blob()
          const url = URL.createObjectURL(blob)
          cache[userId] = { url, ts: Date.now() }
          return url
        }
      } catch {
        /* silencieux */
      }

      cache[userId] = { url: null, ts: Date.now() }
      return null
    })()

    try {
      return await inflight[userId]
    } finally {
      delete inflight[userId]
    }
  }

  return { getUserImageUrl }
}
