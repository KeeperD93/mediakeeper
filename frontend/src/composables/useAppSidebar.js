import { ref, onMounted } from 'vue'
import { fetchApiResponse, useApi } from '@/composables/useApi'

/**
 * Non-presentational logic for AppSidebar: the app version + new-changelog
 * indicator (checked once on mount) and the portal-entry provisioning call.
 * Extracted so AppSidebar.vue stays a presentation layer.
 */
export function useAppSidebar() {
  const { apiPost } = useApi()
  const appVersion = ref('...')
  const hasNewChangelog = ref(false)

  async function provisionPortalEntry() {
    try {
      await apiPost('/api/portal/admin/requests/enter')
    } catch {
      // Non-fatal: navigation will land on the portal login if provisioning failed.
    }
  }

  onMounted(async () => {
    try {
      const res = await fetchApiResponse('/api/changelog/check', { redirectOn401: false })
      if (res.ok) {
        const data = await res.json()
        appVersion.value = data.current_version || '0.0.0'
        hasNewChangelog.value = !!data.has_new
      }
    } catch {
      // Fallback if the changelog-check API isn't ready yet
      try {
        const res = await fetchApiResponse('/api/changelog/current', {
          retryOn401: false,
          redirectOn401: false,
        })
        if (res.ok) {
          const data = await res.json()
          appVersion.value = data.version || '0.0.0'
        }
      } catch {
        /* silent: version display is cosmetic */
      }
    }
  })

  return { appVersion, hasNewChangelog, provisionPortalEntry }
}
