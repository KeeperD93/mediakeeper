import { ref } from 'vue'
import { useApi } from '@/composables/useApi'

export function usePortalAchievements() {
  const { apiGet, loading, error } = useApi()
  const achievements = ref([])
  const myAchievements = ref([])
  const leaderboard = ref([])

  async function fetchAll() {
    try {
      const res = await apiGet('/api/portal/achievements')
      achievements.value = res?.items || []
    } catch { achievements.value = [] }
  }

  async function fetchMine() {
    try {
      const res = await apiGet('/api/portal/achievements/me')
      myAchievements.value = res?.items || []
    } catch { myAchievements.value = [] }
  }

  async function fetchUserAchievements(userId) {
    try {
      const res = await apiGet(`/api/portal/achievements/user/${userId}`)
      return res?.items || []
    } catch { return [] }
  }

  async function fetchLeaderboard(limit = 20) {
    try {
      const res = await apiGet(`/api/portal/achievements/leaderboard?limit=${limit}`)
      leaderboard.value = res?.items || []
    } catch { leaderboard.value = [] }
  }

  return {
    achievements, myAchievements, leaderboard,
    fetchAll, fetchMine, fetchUserAchievements, fetchLeaderboard,
    loading, error,
  }
}
