import { ref } from 'vue'
import { useApi } from '@/composables/useApi'

// Singleton config: the top-bar avatar entry and the settings form share one
// reactive value, so toggling the feature in settings shows/hides the menu
// entry live (no reload). Shape: { enabled, discord_pseudo, webhook_configured }.
const config = ref(null)

export function useFeedbackConfig() {
  const { apiGet, apiPost } = useApi()

  async function loadFeedbackConfig() {
    config.value = await apiGet('/api/feedback/config')
  }

  // Throws on a backend error (apiPost rejects with the detail code); callers
  // localize it via resolveApiError.
  async function saveFeedbackConfig(patch) {
    const res = await apiPost('/api/feedback/config', patch)
    if (res) config.value = res
    return res
  }

  async function testFeedbackLink() {
    return apiPost('/api/feedback/test')
  }

  return { config, loadFeedbackConfig, saveFeedbackConfig, testFeedbackLink }
}
