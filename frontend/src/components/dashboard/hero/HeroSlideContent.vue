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
  /* 95×138 keeps the 2:3 poster ratio at the hero's signature size —
     no spacing token represents this widget-specific footprint. */
  width: 95px;
  height: 138px;
  border-radius: var(--radius-btn);
  background: var(--surface-2);
  flex-shrink: 0;
  overflow: hidden;
  border: var(--border-width) solid var(--border-intense);
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
  /* 28 px placeholder glyph — bigger than --text-xl's max (~32 px at
     wide viewports) is irrelevant here since the poster doesn't
     scale. Kept literal as a hero-only signature. */
  font-size: 28px;
  opacity: 0.3;
  color: var(--text-primary);
}
.hero-poster-clickable {
  cursor: pointer;
}
.hero-poster-audio {
  background: linear-gradient(
    135deg,
    rgb(var(--accent-rgb), 0.15),
    rgb(var(--color-module-subtitles-rgb), 0.1)
  );
  border-color: rgb(var(--color-module-subtitles-rgb), 0.25);
}
.hero-music-icon {
  /* Audio fallback glyph — 32 px sits one step above .hero-poster-ph
     so the music note still reads at poster size. Hero-only literal. */
  font-size: 32px;
  opacity: 0.5;
  color: var(--color-module-subtitles);
}
.hero-info {
  /* Mobile-first basis — reserves space for the 95 px poster + 14 px
     gap (109 px total) so the info column fills the rest of the row
     and elides cleanly. Desktop overrides with ``flex: 1`` for natural
     grow inside the wider hero layout (cf. @media (min-width: 768px)). */
  flex: 1 1 calc(100% - 109px);
  min-width: 0;
}
.hero-badge-label {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-3xs);
  font-weight: var(--font-regular);
  letter-spacing: var(--tracking-widest);
  text-transform: uppercase;
  margin-bottom: var(--space-1);
}
.badge-playing {
  color: var(--color-online);
}
.badge-paused {
  color: var(--color-warning);
}
.badge-audio {
  color: var(--color-module-subtitles);
}
.hero-pulse-dot {
  width: 6px;
  height: 6px;
  border-radius: var(--radius-circle);
  flex-shrink: 0;
  display: inline-block;
  animation: hero-pulse-dot var(--duration-pulse) ease-in-out infinite;
}
.pulse-green {
  background: var(--color-online);
}
.pulse-yellow {
  background: var(--color-warning);
}
.pulse-purple {
  background: var(--color-module-subtitles);
}
@keyframes hero-pulse-dot {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.35;
  }
}
.hero-title {
  /* 22 px is the hero's signature size — between --text-lg (~20.8 px)
     and --text-xl's responsive clamp. Kept literal so the hero stays
     visually identical across viewports. */
  font-size: 22px;
  font-weight: var(--font-medium);
  color: var(--text-primary);
  margin: 0 0 var(--space-half);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: flex;
  align-items: center;
  gap: var(--space-2);
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
  /* 18 px below the --icon-md (16) → --icon-lg (20) step so the Emby
     badge stays balanced against the 22 px title without overpowering
     it. Hero-only literal. */
  width: 18px;
  height: 18px;
}
.hero-sub {
  font-size: var(--text-sm);
  color: var(--text-faint);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.hero-progress {
  margin-top: var(--space-2-5);
  /* 3 px progress bar — below --border-width-thin scale, widget-local. */
  height: 3px;
  background: var(--surface-3);
  border-radius: 2px;
  /* 240 px target width clipped by max-width on narrow viewports —
     hero-only signature. */
  width: 240px;
  max-width: 100%;
}
.hero-progress-fill {
  height: 3px;
  background: linear-gradient(90deg, var(--accent-500), var(--accent-300));
  border-radius: 2px;
  transition: width var(--duration-slower);
}
.anim-slide-up {
  opacity: 0;
  transform: translateY(16px);
  /* 0.6 s — hero-only signature, outside the --duration-* scale
     (slower 0.5, animation 1.5). Single occurrence accepted as a
     literal rather than creating a one-off duration step. */
  animation: hero-slide-up 0.6s ease-out forwards;
}
@keyframes hero-slide-up {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
/* Stagger delays — orchestrate the cascade of hero slide elements
   (poster → info). Sub-second values intentionally unique per stage,
   not tokenized (each delay is one-off by design). */
.stg-30 {
  animation-delay: 0.3s;
}
.stg-45 {
  animation-delay: 0.45s;
}

@media (min-width: 768px) {
  .hero-info {
    /* Desktop — natural flex grow inside the wider hero row. */
    flex: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .hero-pulse-dot {
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
