import { ref } from 'vue'
import { useApi } from '@/composables/useApi'

// Backoffice read of the operator donation config for the top-bar heart
// panel. The portal reads the same shape from its ui.donation payload; the
// backoffice (separate auth) reads it from this dedicated endpoint.
//
// Singleton ``donation`` ref: the dashboard top-bar heart and the admin
// settings form share one reactive value, so saving in settings updates the
// open panel live (no page reload).
const donation = ref(null)

export function useDonationConfig() {
  const { apiGet } = useApi()

  async function loadDonation() {
    donation.value = await apiGet('/api/settings/donation')
  }

  return { donation, loadDonation }
}
