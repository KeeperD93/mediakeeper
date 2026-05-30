<template>
  <Teleport to="body">
    <div v-if="profileOpen" class="up-overlay" @click="profileOpen = false" />
    <Transition name="pop-profile">
      <div v-if="profileOpen" class="up-pop" :style="profileStyle">
        <UpHeader
          :profile-name="profileName"
          :profile-tier="profileTier"
          :profile-avatar-url="profileAvatarUrl"
          :user-profile="userProfile"
          :ticks-to-duration="ticksToDuration"
          @close="profileOpen = false"
        />
        <div v-if="!userProfile" class="up-loading">
          <div class="skel-line w70" />
          <div class="skel-line w50 up-skel-spaced" />
          <div class="skel-line w60 up-skel-spaced" />
        </div>
        <div v-else-if="userProfile._error" class="up-empty up-empty-wide">
          {{ $t('stats.profileError') }}
        </div>
        <template v-else>
          <div class="up-body">
            <UpRanks
              :user-profile="userProfile"
              :last-play-text="lastPlayText"
              :last-meta-text="lastMetaText"
            />
            <UpFluxRadar :user-profile="userProfile" />
          </div>
          <div class="up-section up-section-activity">
            <div class="up-stitle">{{ $t('stats.activity30d') }}</div>
            <div class="up-activity-chart">
              <div
                v-for="d in userProfile.daily_activity"
                :key="d.date"
                class="up-act-bar"
                :style="{ height: upBarH(d.count) + '%' }"
                :title="d.date + ' : ' + d.count + ' lectures'"
              />
            </div>
          </div>
        </template>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'
import { useStatsUI } from '@/composables/useStatsUI'
import { useStats } from '@/composables/useStats'
import UpHeader from './StatsUserProfilePopover/UpHeader.vue'
import UpRanks from './StatsUserProfilePopover/UpRanks.vue'
import UpFluxRadar from './StatsUserProfilePopover/UpFluxRadar.vue'

const { profileOpen, profileName, profileTier, profileAvatarUrl, profileStyle, userProfile } =
  useStatsUI()
const { ticksToDuration, timeAgo } = useStats()

const lastPlayText = computed(() => {
  const p = userProfile.value
  if (!p) return '—'
  return p.last_series ? `${p.last_series} — ${p.last_play || ''}` : p.last_play || '—'
})
const lastMetaText = computed(() => {
  const p = userProfile.value
  if (!p) return ''
  return `${p.last_device || '—'} — ${p.last_client || '—'} — ${p.last_seen ? timeAgo(p.last_seen) : '—'}`
})

function upBarH(v) {
  if (!userProfile.value?.daily_activity) return 0
  const mx = Math.max(...userProfile.value.daily_activity.map(d => d.count), 1)
  return Math.round((v / mx) * 100)
}
</script>

<style scoped>
.up-overlay {
  position: fixed;
  inset: 0;
  z-index: 9900;
  background: rgb(0, 0, 0, 0.3);
}
.up-pop {
  position: fixed;
  z-index: 9901;
  width: 640px;
  max-width: calc(100vw - 24px);
  overflow: hidden;
  background: var(--bg-primary);
  border: 0.5px solid var(--border-default);
  border-radius: var(--radius-card);
  padding: 20px;
  box-shadow: var(--shadow-modal);
}
.pop-profile-enter-active,
.pop-profile-leave-active {
  transition: all var(--duration-base) ease;
}
.pop-profile-enter-from,
.pop-profile-leave-to {
  opacity: 0;
  transform: translateY(6px);
}
.up-loading {
  padding: 20px 0;
}
.up-body {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  min-width: 0;
}
.up-empty {
  font-size: var(--text-2xs);
  color: var(--text-muted);
}
.up-empty-wide {
  padding: 16px 0;
}
.up-stitle {
  font-size: var(--text-3xs);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: rgb(255, 255, 255, 0.3);
  margin-bottom: 8px;
}
.up-activity-chart {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 60px;
  padding: 4px 0;
}
.up-act-bar {
  flex: 1;
  min-width: 0;
  background: rgb(var(--accent-rgb), 0.4);
  border-radius: 2px 2px 0 0;
  transition: height var(--duration-base);
  min-height: 1px;
}
.up-act-bar:hover {
  background: rgb(var(--accent-rgb), 0.7);
}
.skel-line {
  height: 12px;
  border-radius: 4px;
  background: linear-gradient(
    90deg,
    rgb(255, 255, 255, 0.02) 25%,
    rgb(255, 255, 255, 0.05) 50%,
    rgb(255, 255, 255, 0.02) 75%
  );
  background-size: 200% 100%;
  animation: up-sk var(--duration-animation) ease-in-out infinite;
}
.w50 {
  width: 50%;
}
.w60 {
  width: 60%;
}
.w70 {
  width: 70%;
}
@keyframes up-sk {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}
.up-skel-spaced {
  margin-top: 8px;
}
.up-section-activity {
  margin-top: 4px;
}
@media (max-width: 767px) {
  /* Mobile — override the dynamic click-based positioning so the popup stays
   * inside the viewport and scrolls internally instead of getting clipped. */
  .up-pop {
    width: calc(100vw - 24px) !important;
    inset: 12px 12px auto !important;
    transform: none !important;
    max-height: calc(100dvh - 24px);
    overflow-y: auto;    padding: 16px;
  }
  .up-body {
    grid-template-columns: 1fr;
  }
}
</style>
