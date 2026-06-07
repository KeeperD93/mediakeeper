import { ref } from 'vue'
import { useApi } from '@/composables/useApi'

// Donation config rides the shared portal-admin settings endpoint; we
// only read/write the three ``donation.*`` keys (sent under their dotted
// alias). Kept out of the component so it does no HTTP itself (§5).
const ENDPOINT = '/api/portal/admin/settings'

function pick(res) {
  return {
    enabled: !!res?.['donation.enabled'],
    url: res?.['donation.url'] || '',
    message: res?.['donation.message'] || '',
    buttonLabel: res?.['donation.button_label'] || '',
  }
}

export function useDonationAdmin() {
  const { apiGet, apiPatch } = useApi()
  const saving = ref(false)

  async function fetchDonation() {
    return pick(await apiGet(ENDPOINT))
  }

  async function saveDonation(patch) {
    saving.value = true
    try {
      const res = await apiPatch(ENDPOINT, patch)
      return res ? pick(res) : null
    } finally {
      saving.value = false
    }
  }

  return { saving, fetchDonation, saveDonation }
}
