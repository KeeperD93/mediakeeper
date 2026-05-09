<template>
  <div>
    <div class="section-head">
      <h2 class="section-title">{{ $t('stats.nowPlaying') }}</h2>
      <span v-if="activeSessions.length" class="live-badge">
        <span class="live-dot" />
        {{ $t('dashboard.activeCount', { count: playingCount }) }}
      </span>
      <div v-if="sessionPages > 1" class="session-pager">
        <button class="pg-btn" :disabled="sessionPage <= 0" @click="sessionPage--">
          <ChevronLeft :size="10" :stroke-width="2.5" />
        </button>
        <span class="pg-info">{{ sessionPage + 1 }}/{{ sessionPages }}</span>
        <button class="pg-btn" :disabled="sessionPage >= sessionPages - 1" @click="sessionPage++">
          <ChevronRight :size="10" :stroke-width="2.5" />
        </button>
      </div>
    </div>
    <MkEmptyState
      v-if="!activeSessions.length && !loadingSessions"
      :icon="CirclePlay"
      size="sm"
      :title="$t('stats.noPlaying')"
    />
    <div v-if="loadingSessions && !sessions.length" class="session-grid">
      <div v-for="n in 3" :key="n" class="glass-card sess-skel">
        <div class="skel-block skel-block-sess" />
        <div class="sess-skel-body">
          <div class="skel-line w70" />
          <div class="skel-line w40" />
        </div>
      </div>
    </div>
    <div v-else-if="activeSessions.length" class="session-grid">
      <SessionCard
        v-for="s in pagedSessions"
        :key="s.user_id + '_' + s.media"
        :s="s"
        :progress="getSessionProgress(s)"
        :lang-label="langLabel"
        :lang-short="langShort"
        :avatar-colors="avatarColors"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useStats } from '@/composables/useStats'
import { useStatsUI } from '@/composables/useStatsUI'
import { ChevronLeft, ChevronRight, CirclePlay } from 'lucide-vue-next'
import MkEmptyState from '@/components/common/MkEmptyState.vue'
import SessionCard from './StatsSessionsSection/SessionCard.vue'

const { sessions, loadingSessions, getSessionProgress, langLabel, langShort } = useStats()
const { avatarColors } = useStatsUI()

const SESSIONS_PER_PAGE = 9
const sessionPage = ref(0)
const activeSessions = computed(() =>
  sessions.value.filter(
    s =>
      (s.is_playing || s.is_paused) &&
      s.media_type !== 'theme' &&
      !(s.media || '').toLowerCase().includes('theme'),
  ),
)
const sessionPages = computed(() =>
  Math.max(1, Math.ceil(activeSessions.value.length / SESSIONS_PER_PAGE)),
)
const pagedSessions = computed(() =>
  activeSessions.value.slice(
    sessionPage.value * SESSIONS_PER_PAGE,
    (sessionPage.value + 1) * SESSIONS_PER_PAGE,
  ),
)
const playingCount = computed(() => activeSessions.value.filter(s => s.is_playing).length)
</script>

<style scoped>
.section-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}
.section-title {
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--text-primary);
  margin: 0;
}
.live-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: var(--text-2xs);
  font-weight: var(--font-regular);
  padding: 3px 10px;
  border-radius: var(--radius-btn);
  background: rgb(34, 197, 94, 0.1);
  color: var(--color-success);
  backdrop-filter: blur(8px);
  border: 0.5px solid rgb(34, 197, 94, 0.15);
}
.live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #22c55e;
  animation: sess-pulse var(--duration-animation) ease-in-out infinite;
}
.skel-block-sess {
  height: 100px;
}
.sess-skel-body {
  padding: 14px;
}
@keyframes sess-pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.3;
  }
}
.session-pager {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 6px;
}
.pg-btn {
  background: var(--surface-2);
  border: 0.5px solid var(--border-strong);
  color: var(--text-secondary);
  border-radius: var(--radius-sm);
  padding: 4px 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
}
.pg-btn:disabled {
  opacity: 0.3;
  cursor: default;
}
.pg-info {
  font-size: var(--text-2xs);
  color: var(--text-muted);
}

.session-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.sess-skel {
  overflow: hidden;
  background: var(--surface-1);
  backdrop-filter: var(--blur-md);
  border: 0.5px solid var(--border-default);
  border-radius: var(--radius-card);
}
.skel-block {
  border-radius: var(--radius-card);
  background: linear-gradient(
    90deg,
    rgb(255, 255, 255, 0.02) 25%,
    rgb(255, 255, 255, 0.05) 50%,
    rgb(255, 255, 255, 0.02) 75%
  );
  background-size: 200% 100%;
  animation: sess-sk var(--duration-animation) ease-in-out infinite;
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
  animation: sess-sk var(--duration-animation) ease-in-out infinite;
}
.w40 {
  width: 40%;
}
.w70 {
  width: 70%;
}
@keyframes sess-sk {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

@media (max-width: 1280px) {
  .session-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 768px) {
  .session-grid {
    grid-template-columns: 1fr;
  }
}
</style>
