import { ref } from 'vue'
import { useApi } from '@/composables/useApi'

// User-lists live in ``usePortalLists``; this composable keeps only
// ratings + release reminders (the two other /social endpoints).
export function usePortalSocial() {
  const { apiGet, apiPost, apiDelete, loading, error } = useApi()
  const ratings = ref([])
  const reminders = ref([])

  // Ratings
  async function rateMedia(data) {
    return await apiPost('/api/portal/social/ratings', data)
  }

  async function fetchRatings(tmdbId, mediaType) {
    const res = await apiGet(`/api/portal/social/ratings/${tmdbId}/${mediaType}`)
    if (res) ratings.value = res.items
  }

  async function toggleLike(ratingId) {
    return await apiPost(`/api/portal/social/ratings/${ratingId}/like`)
  }

  // Reminders
  async function fetchReminders() {
    const res = await apiGet('/api/portal/social/reminders')
    if (res) reminders.value = res.items
  }

  async function addReminder(tmdbId, mediaType) {
    return await apiPost('/api/portal/social/reminders', {
      tmdb_id: tmdbId,
      media_type: mediaType,
    })
  }

  async function removeReminder(tmdbId) {
    return await apiDelete(`/api/portal/social/reminders/${tmdbId}`)
  }

  return {
    ratings,
    reminders,
    rateMedia,
    fetchRatings,
    toggleLike,
    fetchReminders,
    addReminder,
    removeReminder,
    loading,
    error,
  }
}
