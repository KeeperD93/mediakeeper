<template>
  <div
    class="hero-poster hero-poster-clickable anim-slide-up stg-30"
    :class="{ 'hero-poster-audio': isAudio }"
    @click="emit('open-fullscreen', current)"
  >
    <img
      v-if="current.thumb_url && !posterError"
      :src="current.thumb_url"
      class="hero-poster-img"
      @error="posterError = true"
    />
    <span v-else-if="isAudio" class="hero-poster-ph hero-music-icon">♫</span>
    <span v-else class="hero-poster-ph">▶</span>
  </div>
  <div class="hero-info anim-slide-up stg-45">
    <span
      class="hero-badge-label"
      :class="current.is_playing ? (isAudio ? 'badge-audio' : 'badge-playing') : 'badge-paused'"
    >
      <span
        class="hero-pulse-dot"
        :class="current.is_playing ? (isAudio ? 'pulse-purple' : 'pulse-green') : 'pulse-yellow'"
      />
      {{
        isAudio
          ? current.is_playing
            ? $t('dashboard.listening')
            : $t('dashboard.paused')
          : current.is_playing
            ? $t('dashboard.playing')
            : $t('dashboard.paused')
      }}
    </span>
    <p class="hero-title hero-title-clickable" @click="emit('open-fullscreen', current)">
      {{ current.series || current.media }}
      <a
        v-if="currentEmbyUrl"
        :href="currentEmbyUrl"
        target="_blank"
        rel="noopener"
        class="hero-emby-link"
        :title="$t('dashboard.viewOnEmby')"
        @click.stop
      >
        <img src="/assets/icons/emby.svg" class="hero-emby-icon" alt="Emby" />
      </a>
    </p>
    <p class="hero-sub">
      {{
        current.episode
          ? `${current.episode} · ${current.media}`
          : current.media_type || $t('common.film')
      }}
      —
      {{
        $t('dashboard.userOnDevice', {
          user: current.user,
          device: current.client || current.device || $t('common.unknown'),
        })
      }}
    </p>
    <div class="hero-progress">
      <div class="hero-progress-fill" :style="{ width: (current.progress || 0) + '%' }" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  current: { type: Object, default: () => ({}) },
  isAudio: { type: Boolean, default: false },
  embyBaseUrl: { type: String, default: '' },
  embyServerId: { type: String, default: '' },
})
const emit = defineEmits(['open-fullscreen'])

const posterError = ref(false)
watch(
  () => props.current,
  () => {
    posterError.value = false
  },
)

// Emby Web 4.9+ resolves the item route only when ``serverId`` is
// present in the query — without it the SPA shell loads but the page
// stays blank. Mirrors the portal helper ``build_emby_deep_link``.
const currentEmbyUrl = computed(() => {
  const s = props.current
  if (!props.embyBaseUrl || !s.item_id) return ''
  let url = `${props.embyBaseUrl}/web/index.html#!/item?id=${s.item_id}`
  if (props.embyServerId) url += `&serverId=${props.embyServerId}`
  return url
})
</script>

<style scoped>
.hero-poster {
  width: 95px;
  height: 138px;
  border-radius: var(--radius-btn);
  background: var(--surface-2);
  flex-shrink: 0;
  overflow: hidden;
  border: 1px solid rgb(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-md);
}
.hero-poster-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.hero-poster-ph {
  font-size: 28px;
  opacity: 0.3;
  color: var(--text-primary);
}
.hero-poster-clickable {
  cursor: pointer;
}
.hero-poster-audio {
  background: linear-gradient(135deg, rgb(99, 102, 241, 0.15), rgb(167, 139, 250, 0.1));
  border-color: rgb(139, 132, 255, 0.25);
}
.hero-music-icon {
  font-size: 32px;
  opacity: 0.5;
  color: #a78bfa;
}
.hero-info {
  flex: 1;
  min-width: 0;
}
.hero-badge-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--text-3xs);
  font-weight: var(--font-regular);
  letter-spacing: 1px;
  text-transform: uppercase;
  margin-bottom: 4px;
}
.badge-playing {
  color: #22c55e;
}
.badge-paused {
  color: #facc15;
}
.badge-audio {
  color: #a78bfa;
}
.hero-pulse-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
  position: relative;
  display: inline-block;
}
.pulse-green {
  background: #22c55e;
}
.pulse-yellow {
  background: #facc15;
}
.pulse-purple {
  background: #a78bfa;
}
.pulse-green::after,
.pulse-yellow::after,
.pulse-purple::after {
  content: '';
  position: absolute;
  inset: -3px;
  border-radius: 50%;
  animation: hero-pulse var(--duration-pulse) ease-out infinite;
}
.pulse-green::after {
  background: rgb(34, 197, 94, 0.5);
}
.pulse-yellow::after {
  background: rgb(250, 204, 21, 0.5);
}
.pulse-purple::after {
  background: rgb(167, 139, 250, 0.5);
}
@keyframes hero-pulse {
  0% {
    transform: scale(1);
    opacity: 0.7;
  }
  70% {
    transform: scale(2.5);
    opacity: 0;
  }
  100% {
    transform: scale(2.5);
    opacity: 0;
  }
}
.hero-title {
  font-size: 22px;
  font-weight: var(--font-medium);
  color: var(--text-primary);
  margin: 0 0 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: flex;
  align-items: center;
  gap: 8px;
}
.hero-title-clickable {
  cursor: pointer;
}
.hero-emby-link {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
  opacity: 0.35;
  transition: opacity var(--duration-base);
}
.hero-emby-link:hover {
  opacity: 0.8;
}
.hero-emby-icon {
  width: 18px;
  height: 18px;
}
.hero-sub {
  font-size: var(--text-sm);
  color: rgb(255, 255, 255, 0.45);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.hero-progress {
  margin-top: 10px;
  height: 3px;
  background: rgb(255, 255, 255, 0.1);
  border-radius: 2px;
  width: 240px;
  max-width: 100%;
}
.hero-progress-fill {
  height: 3px;
  background: linear-gradient(90deg, #6366f1, #818cf8);
  border-radius: 2px;
  transition: width var(--duration-slower);
}
.anim-slide-up {
  opacity: 0;
  transform: translateY(16px);
  animation: hero-slide-up 0.6s ease-out forwards;
}
@keyframes hero-slide-up {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
.stg-30 {
  animation-delay: 0.3s;
}
.stg-45 {
  animation-delay: 0.45s;
}

@media (max-width: 767px) {
  .hero-info {
    flex: 1 1 calc(100% - 109px);
    min-width: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .pulse-green::after,
  .pulse-yellow::after,
  .pulse-purple::after {
    animation: none;
  }
  .anim-slide-up {
    animation: none;
    opacity: 1;
    transform: none;
  }
  .hero-progress-fill {
    transition: none;
  }
}
</style>
