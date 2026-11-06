import { useApi } from '@/composables/useApi'

const BASE = '/api/portal/admin/debug'

/** Calls behind the portal's debug tools: XP, levels, trophies, checks on every player. */
export function usePortalAdminDebug() {
  const { apiGet, apiPost } = useApi()

  return {
    listUsers: async () => (await apiGet(`${BASE}/users`))?.items || [],
    listAchievements: async () => (await apiGet(`${BASE}/achievements`))?.items || [],
    grantXp: (userId, amount, note) =>
      apiPost(`${BASE}/grant-xp`, { user_id: userId, amount, note }),
    setLevel: (userId, level) => apiPost(`${BASE}/set-level`, { user_id: userId, level }),
    unlockAchievement: (userId, achievementId) =>
      apiPost(`${BASE}/unlock-achievement`, { user_id: userId, achievement_id: achievementId }),
    lockAchievement: (userId, achievementId) =>
      apiPost(`${BASE}/lock-achievement`, { user_id: userId, achievement_id: achievementId }),
    resetAchievementForAll: achievementId =>
      apiPost(`${BASE}/reset-achievement-for-all`, { achievement_id: achievementId }),
    recheckAllAchievements: () => apiPost(`${BASE}/recheck-all-achievements`, {}),
  }
}
