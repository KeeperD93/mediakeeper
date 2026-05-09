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
        @open-fullscreen="emit('open-fullscreen', $event)"
      />
      <HeroSessionStrip
        v-if="sessions.length > 1"
        :sessions="sessions"
        :idx="idx"
        @go-to="goTo"
      />
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
  height: 340px;
  overflow: hidden;
  background: var(--hero-bg, #0a0e1a);
  opacity: 0;
  transform: scale(1.02);
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
  bottom: 28px;
  left: 28px;
  right: 28px;
  display: flex;
  align-items: flex-end;
  gap: 16px;
  z-index: 2;
}

@media (max-width: 767px) {
  .hero-content {
    flex-wrap: wrap;
    bottom: 20px;
    left: 18px;
    right: 18px;
    gap: 14px;
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
