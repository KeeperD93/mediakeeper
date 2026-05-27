<template>
  <div class="hero-wrap" :class="{ 'hero-entered': entered }">
    <HeroBackdrop
      :current-poster="currentPoster"
      :is-audio="isAudio"
      :genre-ids="current.genre_ids || []"
      :idle="sessions.length === 0"
    />
    <HeroConnectedDropdown :all-sessions="allSessions" />
    <div v-if="sessions.length === 0" class="hero-empty">
      <MkEmptyState :title="$t('dashboard.noSessions')" />
    </div>
    <div v-else class="hero-content">
      <HeroSlideContent
        :current="current"
        :is-audio="isAudio"
        :emby-base-url="embyBaseUrl"
        :emby-server-id="embyServerId"
        @open-fullscreen="emit('open-fullscreen', $event)"
      />
      <HeroSessionStrip v-if="sessions.length > 1" :sessions="sessions" :idx="idx" @go-to="goTo" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, toRef, onMounted } from 'vue'
import { useHeroAutoplay } from '@/composables/useHeroAutoplay'
import HeroBackdrop from './hero/HeroBackdrop.vue'
import HeroSlideContent from './hero/HeroSlideContent.vue'
import HeroSessionStrip from './hero/HeroSessionStrip.vue'
import HeroConnectedDropdown from './hero/HeroConnectedDropdown.vue'
import MkEmptyState from '@/components/common/MkEmptyState.vue'

const props = defineProps({
  sessions: { type: Array, default: () => [] },
  allSessions: { type: Array, default: () => [] },
  embyBaseUrl: { type: String, default: '' },
  embyServerId: { type: String, default: '' },
})
const emit = defineEmits(['open-fullscreen'])

const sessionsRef = toRef(props, 'sessions')
const { idx, current, goTo } = useHeroAutoplay(sessionsRef)

const isAudio = computed(() => current.value.media_type === 'Audio')
const currentPoster = computed(() => current.value.thumb_url || '')

const entered = ref(false)
onMounted(() => {
  requestAnimationFrame(() => {
    entered.value = true
  })
})
</script>

<style scoped>
.hero-wrap {
  position: relative;
  /* 240 px is the hero's signature height — outside the spacing scale
     since the hero is a landing-page banner, not a card. */
  height: 240px;
  overflow: hidden;
  background: var(--hero-bg);
  opacity: 0;
  transform: scale(1.02);
  /* 0.8 s — hero-only mount transition, outside the --duration-*
     scale (slower 0.5, animation 1.5). Single occurrence accepted
     as a literal rather than introducing a one-off duration token. */
  transition:
    opacity 0.8s ease,
    transform 0.8s ease;
}
.hero-wrap.hero-entered {
  opacity: 1;
  transform: scale(1);
}
.hero-empty {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 2;
}
.hero-content {
  position: absolute;
  display: flex;
  align-items: flex-end;
  z-index: 2;
  /* Mobile-first paddings + wrap — keeps the avatar stack inside the
     viewport on phones. Desktop relaxes (no wrap, 28 px insets, larger
     gap) via the @media (min-width: 768px) block. */
  flex-wrap: wrap;
  bottom: var(--space-5);
  /* 18 px hero-only inset on phones — between --space-4 and --space-5
     to keep the avatar stack from kissing the viewport edge. */
  left: 18px;
  right: 18px;
  gap: var(--space-3-5);
}

@media (min-width: 768px) {
  .hero-content {
    flex-wrap: nowrap;
    /* 28 px content inset — slightly above --space-6 (24) to give the
       hero its airy footprint while staying close to the 8 px grid. */
    bottom: 28px;
    left: 28px;
    right: 28px;
    gap: var(--space-4);
  }
}

@media (prefers-reduced-motion: reduce) {
  .hero-wrap {
    transition: none;
    opacity: 1;
    transform: none;
  }
}
</style>
