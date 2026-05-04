<template>
  <div class="pt-leaderboard">
    <div class="pt-lb-header">
      <h2>{{ $t('portal.tabs.leaderboard') }}</h2>
    </div>

    <div v-if="leaderboard.length >= 3" class="pt-lb-podium">
      <div
        v-for="(user, idx) in leaderboard.slice(0, 3)"
        :key="user.user_id"
        class="pt-lb-podium-item"
        :class="`pt-lb-rank-${idx + 1}`"
      >
        <MkAvatar
          :src="user.avatar_url"
          :name="user.display_name || ''"
          :size="56"
          class="pt-lb-avatar"
        />
        <div class="pt-lb-rank">#{{ idx + 1 }}</div>
        <div class="pt-lb-name">{{ user.display_name }}</div>
        <div class="pt-lb-xp">{{ $t('portal.level') }} {{ user.level }} · {{ user.xp }} XP</div>
        <div class="pt-lb-badges-count">
          {{ $t('portal.achievements.count', user.achievements_count) }}
        </div>
      </div>
    </div>

    <div class="pt-lb-table">
      <div v-for="(user, idx) in leaderboard.slice(3)" :key="user.user_id" class="pt-lb-row">
        <span class="pt-lb-pos">#{{ idx + 4 }}</span>
        <span class="pt-lb-row-name">{{ user.display_name }}</span>
        <span class="pt-lb-row-level">{{ $t('portal.level') }} {{ user.level }}</span>
        <span class="pt-lb-row-xp">{{ user.xp }} XP</span>
      </div>
    </div>

    <h3 class="pt-section-title">{{ $t('portal.achievements.myProgress') }}</h3>
    <div class="pt-badge-grid">
      <AchievementBadge
        v-for="ach in myAchievements"
        :key="ach.achievement_id"
        :achievement="ach"
        :progress="ach.progress"
        :unlocked="ach.unlocked"
      />
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { usePortalAchievements } from '@/composables/portal/usePortalAchievements'
import AchievementBadge from '@/components/portal/AchievementBadge.vue'
import MkAvatar from '@/components/common/MkAvatar.vue'

const { leaderboard, myAchievements, fetchLeaderboard, fetchMine } = usePortalAchievements()

onMounted(async () => {
  await Promise.all([fetchLeaderboard(), fetchMine()])
})
</script>

<style scoped>
.pt-leaderboard {
  max-width: 900px;
  margin: 0 auto;
  padding: 1.5rem;
}
.pt-lb-header {
  margin-bottom: 1.5rem;
}
.pt-lb-header h2 {
  font-size: var(--portal-text-xl);
  font-weight: var(--portal-font-bold);
  color: var(--text-primary);
}
.pt-lb-podium {
  display: flex;
  justify-content: center;
  gap: 1rem;
  margin-bottom: 2rem;
}
.pt-lb-podium-item {
  text-align: center;
  padding: 1.25rem 1rem;
  background: var(--bg-secondary);
  border-radius: var(--radius-card);
  border: 1px solid var(--border);
  width: 180px;
}
.pt-lb-rank-1 {
  order: 2;
  border-color: #eab308;
}
.pt-lb-rank-2 {
  order: 1;
  border-color: #94a3b8;
}
.pt-lb-rank-3 {
  order: 3;
  border-color: #b45309;
}
.pt-lb-avatar {
  margin: 0 auto 0.5rem;
}
.pt-lb-rank {
  font-size: var(--portal-text-2xl);
  font-weight: var(--portal-font-extrabold);
  color: var(--accent);
}
.pt-lb-name {
  font-size: var(--portal-text-base);
  font-weight: var(--portal-font-medium);
  color: var(--text-primary);
}
.pt-lb-xp {
  font-size: var(--portal-text-xs);
  color: var(--text-muted);
}
.pt-lb-badges-count {
  font-size: var(--portal-text-2xs);
  color: var(--text-muted);
  margin-top: 0.25rem;
}
.pt-lb-table {
  margin-bottom: 2rem;
}
.pt-lb-row {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.6rem 1rem;
  border-bottom: 1px solid var(--border);
}
.pt-lb-pos {
  font-weight: var(--portal-font-bold);
  color: var(--text-muted);
  width: 2.5rem;
}
.pt-lb-row-name {
  flex: 1;
  font-weight: var(--portal-font-medium);
  color: var(--text-primary);
}
.pt-lb-row-level {
  font-size: var(--portal-text-xs);
  color: var(--text-secondary);
}
.pt-lb-row-xp {
  font-size: var(--portal-text-xs);
  color: var(--accent);
  font-weight: var(--portal-font-medium);
}
.pt-section-title {
  font-size: var(--portal-text-md);
  font-weight: var(--portal-font-bold);
  color: var(--text-primary);
  margin-bottom: 1rem;
}
.pt-badge-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 0.75rem;
}
</style>
