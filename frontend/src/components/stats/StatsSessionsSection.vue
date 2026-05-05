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
      <div v-for="s in pagedSessions" :key="s.user_id + '_' + s.media" class="glass-card sess-card">
        <div class="sc-backdrop">
          <img
            v-if="s.backdrop_url"
            :src="s.backdrop_url"
            class="sc-backdrop-img"
            @error="e => (e.target.style.display = 'none')"
          />
          <div class="sc-backdrop-overlay" />
        </div>
        <div class="sc-inner">
          <div class="sc-left">
            <img
              v-if="s.thumb_url"
              :src="s.thumb_url"
              class="sc-poster"
              @error="e => (e.target.style.display = 'none')"
            />
            <div v-else class="sc-poster sc-poster-empty">
              <CirclePlay class="sc-poster-empty-icon" :size="18" />
            </div>
            <span v-if="langShort(s.audio_language)" class="sc-lang">
              {{ langShort(s.audio_language) }}
            </span>
          </div>
          <div class="sc-right">
            <div class="sc-top-row">
              <div class="sc-title">
                {{ s.series || s.media }}{{ s.series ? ' — ' + s.media : '' }}
              </div>
              <span class="sc-badge" :class="s.is_playing ? 'badge-on' : 'badge-off'">
                <Play v-if="s.is_playing" :size="7" fill="currentColor" />
                <Pause v-else :size="7" fill="currentColor" />
                {{ s.is_playing ? $t('dashboard.playing') : $t('dashboard.paused') }}
              </span>
            </div>
            <div v-if="s.episode" class="sc-episode">{{ s.episode }}</div>
            <div class="sc-details">
              <span class="sc-dk">{{ $t('common.user') }}</span>
              <span class="sc-dv">{{ s.user }}</span>
              <span class="sc-dk">{{ $t('common.device') }}</span>
              <span class="sc-dv">{{ s.device }}</span>
              <span class="sc-dk">{{ $t('stats.video') }}</span>
              <span class="sc-dv" :class="s.video_decision === 'Transcode' ? 'c-amber' : 'c-green'">
                {{
                  s.video_decision === 'Transcode'
                    ? $t('stats.transcodeLabel')
                    : $t('stats.directPlay')
                }}
                ({{ s.video_codec }}{{ s.video_height ? ' ' + s.video_height + 'p' : '' }})
              </span>
              <span class="sc-dk">{{ $t('stats.audio') }}</span>
              <span class="sc-dv" :class="s.audio_decision === 'Transcode' ? 'c-amber' : 'c-green'">
                {{
                  s.audio_decision === 'Transcode'
                    ? $t('stats.transcodeLabel')
                    : $t('stats.directPlay')
                }}
                ({{ s.audio_codec }}{{ s.audio_channels ? '-' + s.audio_channels + 'Ch' : '' }})
              </span>
              <template v-if="s.audio_language">
                <span class="sc-dk">{{ $t('stats.audioLanguage') }}</span>
                <span class="sc-dv">{{ langLabel(s.audio_language) }}</span>
              </template>
              <template v-if="s.subtitle_language">
                <span class="sc-dk">{{ $t('stats.subtitles') }}</span>
                <span class="sc-dv">{{ langLabel(s.subtitle_language) }}</span>
              </template>
              <span class="sc-dk">{{ $t('stats.eta') }}</span>
              <span class="sc-dv">{{ s.eta || '—' }}</span>
            </div>
            <div class="sc-time">
              {{ getSessionProgress(s).position }} / {{ getSessionProgress(s).duration }}
            </div>
          </div>
        </div>
        <div class="sc-progress">
          <div
            class="sc-progress-fill"
            :class="s.is_paused ? 'paused' : ''"
            :style="{ width: getSessionProgress(s).pct + '%' }"
          />
        </div>
        <div class="sc-footer">
          <Play v-if="s.is_playing" :size="7" fill="#4ade80" />
          <Pause v-else :size="7" fill="#facc15" />
          <span class="sc-ft-title">{{ s.series || s.media }}</span>
          <span class="sc-ft-user">{{ s.user }}</span>
          <div class="sc-ft-avatar" :style="{ background: avatarColors[0] }">
            {{ (s.user || '?')[0].toUpperCase() }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useStats } from '@/composables/useStats'
import { useStatsUI } from '@/composables/useStatsUI'
import { ChevronLeft, ChevronRight, CirclePlay, Pause, Play } from 'lucide-vue-next'
import MkEmptyState from '@/components/common/MkEmptyState.vue'

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
.sc-poster-empty-icon {
  opacity: 0.3;
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
.sess-card {
  overflow: hidden;
  display: flex;
  flex-direction: column;
  position: relative;
  background: var(--surface-1);
  backdrop-filter: var(--blur-md);
  border: 0.5px solid var(--border-default);
  border-radius: var(--radius-card);
}
.sess-card:hover {
  border-color: rgb(var(--accent-rgb), 0.15);
  transform: translateY(-2px);
}
.sess-skel {
  overflow: hidden;
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

.sc-backdrop {
  position: absolute;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  border-radius: var(--radius-card);
}
.sc-backdrop-img {
  position: absolute;
  inset: -20px;
  width: calc(100% + 40px);
  height: calc(100% + 40px);
  object-fit: cover;
  filter: blur(18px) brightness(0.3) saturate(1.4);
  transform: scale(1.1);
}
.sc-backdrop-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    135deg,
    rgb(3, 7, 18, 0.75) 0%,
    rgb(3, 7, 18, 0.55) 50%,
    rgb(3, 7, 18, 0.75) 100%
  );
}
.sc-inner {
  display: flex;
  gap: 0;
  flex: 1;
  position: relative;
  z-index: 1;
}
.sc-left {
  position: relative;
  flex-shrink: 0;
  width: 140px;
}
.sc-poster {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  min-height: 160px;
}
.sc-poster-empty {
  width: 100%;
  height: 100%;
  min-height: 160px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgb(255, 255, 255, 0.03);
}
.sc-lang {
  position: absolute;
  top: 6px;
  left: 6px;
  font-size: 0.5rem;
  font-weight: var(--font-bold);
  background: rgb(0, 0, 0, 0.7);
  color: #fff;
  padding: 2px 5px;
  border-radius: 3px;
  z-index: 2;
  backdrop-filter: blur(4px);
}
.sc-right {
  flex: 1;
  min-width: 0;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
}
.sc-top-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 2px;
}
.sc-badge {
  font-size: 0.55rem;
  font-weight: var(--font-medium);
  padding: 2px 7px;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  gap: 3px;
  flex-shrink: 0;
  white-space: nowrap;
  backdrop-filter: var(--blur-xs);
}
.badge-on {
  background: rgb(34, 197, 94, 0.2);
  color: var(--color-success);
}
.badge-off {
  background: rgb(250, 204, 21, 0.2);
  color: #facc15;
}
.sc-title {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
  text-shadow: 0 1px 3px rgb(0, 0, 0, 0.4);
}
.sc-episode {
  font-size: var(--text-3xs);
  color: rgb(255, 255, 255, 0.6);
  margin-top: 1px;
}
.sc-details {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 1px 8px;
  margin-top: 6px;
}
.sc-dk {
  font-size: 0.58rem;
  text-transform: uppercase;
  color: var(--text-faint);
  letter-spacing: 0.3px;
  padding: 2px 0;
}
.sc-dv {
  font-size: var(--text-2xs);
  color: rgb(255, 255, 255, 0.85);
  padding: 2px 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.c-amber {
  color: var(--color-warning);
}
.c-green {
  color: var(--color-success);
}
.sc-time {
  text-align: right;
  font-size: var(--text-2xs);
  font-family: 'SF Mono', 'Cascadia Mono', monospace;
  color: rgb(255, 255, 255, 0.8);
  margin-top: auto;
  padding-top: 6px;
}
.sc-progress {
  height: 2px;
  background: rgb(255, 255, 255, 0.08);
  position: relative;
  z-index: 1;
}
.sc-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent-500), var(--accent-400));
  transition: width 1s linear;
}
.sc-progress-fill.paused {
  background: linear-gradient(90deg, #f59e0b, #facc15);
}
.sc-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: rgb(0, 0, 0, 0.3);
  border-radius: 0 0 14px 14px;
  position: relative;
  z-index: 1;
  backdrop-filter: blur(4px);
}
.sc-ft-title {
  flex: 1;
  font-size: var(--text-2xs);
  color: rgb(255, 255, 255, 0.7);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.sc-ft-user {
  font-size: var(--text-2xs);
  color: rgb(255, 255, 255, 0.5);
}
.sc-ft-avatar {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.55rem;
  font-weight: var(--font-bold);
  color: #fff;
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
