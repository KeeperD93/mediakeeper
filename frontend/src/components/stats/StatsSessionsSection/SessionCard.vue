<template>
  <div class="glass-card sess-card">
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
          <div class="sc-title">{{ s.series || s.media }}{{ s.series ? ' — ' + s.media : '' }}</div>
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
              s.video_decision === 'Transcode' ? $t('stats.transcodeLabel') : $t('stats.directPlay')
            }}
            ({{ s.video_codec }}{{ s.video_height ? ' ' + s.video_height + 'p' : '' }})
          </span>
          <span class="sc-dk">{{ $t('stats.audio') }}</span>
          <span class="sc-dv" :class="s.audio_decision === 'Transcode' ? 'c-amber' : 'c-green'">
            {{
              s.audio_decision === 'Transcode' ? $t('stats.transcodeLabel') : $t('stats.directPlay')
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
        <div class="sc-time">{{ progress.position }} / {{ progress.duration }}</div>
      </div>
    </div>
    <div class="sc-progress">
      <div
        class="sc-progress-fill"
        :class="s.is_paused ? 'paused' : ''"
        :style="{ width: progress.pct + '%' }"
      />
    </div>
    <div class="sc-footer">
      <Play v-if="s.is_playing" :size="7" fill="#4ade80" />
      <Pause v-else :size="7" fill="#facc15" />
      <span class="sc-ft-title">{{ s.series || s.media }}</span>
      <span class="sc-ft-user">{{ s.user }}</span>
      <MkAvatar
        :src="s.avatar_url || null"
        :name="s.user || '?'"
        :size="18"
        :tier="s.tier || 'bronze'"
        class="sc-ft-avatar"
      />
    </div>
  </div>
</template>

<script setup>
import { CirclePlay, Pause, Play } from 'lucide-vue-next'
import MkAvatar from '@/components/common/MkAvatar.vue'

defineProps({
  s: { type: Object, required: true },
  progress: { type: Object, required: true },
  langLabel: { type: Function, required: true },
  langShort: { type: Function, required: true },
  avatarColors: { type: Array, required: true },
})
</script>

<style scoped>
.glass-card {
  background: var(--surface-1);
  backdrop-filter: var(--blur-md);
  border: 0.5px solid var(--border-default);
  border-radius: var(--radius-card);
}
.sess-card {
  overflow: hidden;
  display: flex;
  flex-direction: column;
  position: relative;
}
.sess-card:hover {
  border-color: rgb(var(--accent-rgb), 0.15);
  transform: translateY(-2px);
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
    rgb(var(--bg-primary-rgb), 0.75) 0%,
    rgb(var(--bg-primary-rgb), 0.55) 50%,
    rgb(var(--bg-primary-rgb), 0.75) 100%
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
  background: var(--surface-1);
}
.sc-poster-empty-icon {
  opacity: 0.3;
}
.sc-lang {
  position: absolute;
  top: 6px;
  left: 6px;
  font-size: 0.5rem;
  font-weight: var(--font-bold);
  background: rgb(0, 0, 0, 0.7);
  color: var(--text-primary);
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
  color: var(--text-primary);
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
  background: var(--surface-3);
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
  color: var(--text-primary);
}
</style>
