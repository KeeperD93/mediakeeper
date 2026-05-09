<template>
  <div v-if="isAudio" class="hero-audio-bg">
    <div
      v-for="i in 5"
      :key="i"
      class="hero-audio-wave"
      :style="{ animationDelay: i * 0.15 + 's' }"
    />
  </div>
  <template v-else>
    <div
      class="hero-backdrop-layer kb-a"
      :class="{ visible: showA, idle }"
      :style="{ backgroundImage: backdropA ? `url(${backdropA})` : 'none' }"
    />
    <div
      class="hero-backdrop-layer kb-b"
      :class="{ visible: !showA, idle }"
      :style="{ backgroundImage: backdropB ? `url(${backdropB})` : 'none' }"
    />
  </template>
  <div class="hero-overlay-bottom" />
  <div class="hero-overlay-top" />
  <div class="hero-ambiance" :style="ambianceStyle" />
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'

const props = defineProps({
  currentPoster: { type: String, default: '' },
  isAudio: { type: Boolean, default: false },
  genreIds: { type: Array, default: () => [] },
  idle: { type: Boolean, default: false },
})

const showA = ref(true)
const backdropA = ref(null)
const backdropB = ref(null)

watch(
  () => props.currentPoster,
  u => {
    if (showA.value) {
      backdropB.value = u
      showA.value = false
    } else {
      backdropA.value = u
      showA.value = true
    }
  },
)

onMounted(() => {
  if (props.currentPoster) backdropA.value = props.currentPoster
})

const GENRE_COLORS = {
  28: 'rgba(239,68,68,0.12)',
  12: 'rgba(245,158,11,0.1)',
  16: 'rgba(59,130,246,0.1)',
  35: 'rgba(251,191,36,0.1)',
  18: 'rgba(99,102,241,0.1)',
  14: 'rgba(168,85,247,0.12)',
  27: 'rgba(220,38,38,0.15)',
  878: 'rgba(6,182,212,0.12)',
  53: 'rgba(55,65,81,0.15)',
  10759: 'rgba(239,68,68,0.1)',
  10765: 'rgba(6,182,212,0.1)',
}

const ambianceStyle = computed(() => {
  for (const gid of props.genreIds || []) {
    if (GENRE_COLORS[gid]) return { background: GENRE_COLORS[gid] }
  }
  return { background: 'transparent' }
})
</script>

<style scoped>
.hero-backdrop-layer {
  position: absolute;
  inset: -20px;
  z-index: 0;
  background-size: cover;
  background-position: center;
  filter: blur(10px) brightness(0.55) saturate(1.4);
  opacity: 0;
  transition: opacity 1.2s ease;
  will-change: transform;
}
.hero-backdrop-layer.visible {
  opacity: 1;
}
.hero-backdrop-layer.kb-a {
  animation: ken-burns-a 20s ease-in-out infinite alternate;
}
.hero-backdrop-layer.kb-b {
  animation: ken-burns-b 22s ease-in-out infinite alternate;
}
.hero-backdrop-layer.idle {
  animation: ken-burns-idle 30s ease-in-out infinite alternate;
}
@keyframes ken-burns-a {
  0% {
    transform: scale(1.05) translate(0, 0);
  }
  100% {
    transform: scale(1.15) translate(-15px, -10px);
  }
}
@keyframes ken-burns-b {
  0% {
    transform: scale(1.08) translate(10px, 5px);
  }
  100% {
    transform: scale(1.18) translate(-10px, -15px);
  }
}
@keyframes ken-burns-idle {
  0% {
    transform: scale(1.02) translate(0, 0);
  }
  100% {
    transform: scale(1.08) translate(-8px, -5px);
  }
}
.hero-ambiance {
  position: absolute;
  inset: 0;
  z-index: 0;
  transition: background 1.5s ease;
  pointer-events: none;
}
.hero-overlay-bottom {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 160px;
  background: linear-gradient(to top, var(--dash-bg, #060a14), transparent);
  z-index: 1;
  pointer-events: none;
}
.hero-overlay-top {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 60px;
  background: linear-gradient(to bottom, rgb(6, 10, 20, 0.6), transparent);
  z-index: 1;
  pointer-events: none;
}
.hero-audio-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
  background: linear-gradient(135deg, #1a0533 0%, #0d1b2a 40%, #1a0533 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0 30%;
}
.hero-audio-wave {
  width: 4px;
  height: 40px;
  background: rgb(139, 132, 255, 0.3);
  border-radius: 2px;
  animation: audio-wave 1.2s ease-in-out infinite alternate;
}
@keyframes audio-wave {
  0% {
    height: 20px;
    opacity: 0.3;
  }
  100% {
    height: 80px;
    opacity: 0.6;
  }
}

@media (prefers-reduced-motion: reduce) {
  .hero-backdrop-layer,
  .hero-backdrop-layer.kb-a,
  .hero-backdrop-layer.kb-b,
  .hero-backdrop-layer.idle {
    animation: none;
    transition: none;
  }
  .hero-ambiance {
    transition: none;
  }
  .hero-audio-wave {
    animation: none;
    height: 40px;
    opacity: 0.45;
  }
}
</style>
