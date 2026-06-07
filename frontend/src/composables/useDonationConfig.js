import { ref } from 'vue'
import { useApi } from '@/composables/useApi'

// Backoffice read of the operator donation config for the top-bar heart
// panel. The portal reads the same shape from its ui.donation payload; the
// backoffice (separate auth) reads it from this dedicated endpoint.
export function useDonationConfig() {
  const { apiGet } = useApi()
  const donation = ref(null)

  async function loadDonation() {
    donation.value = await apiGet('/api/settings/donation')
  }

  return { donation, loadDonation }
}
