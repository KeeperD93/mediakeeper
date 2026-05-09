<template>
  <div class="pt-wrapped" @click="nextSlide">
    <transition name="pt-slide" mode="out-in">
      <div :key="currentSlide" class="pt-wrapped-slide" :class="`pt-slide-${currentSlide}`">
        <template v-if="currentSlide === 0">
          <h1 class="pt-wrapped-title">{{ $t('portal.wrapped.yourYear') }}</h1>
          <p class="pt-wrapped-sub">{{ $t('portal.wrapped.tapToContinue') }}</p>
        </template>

        <template v-else-if="currentSlide === 1">
          <p class="pt-wrapped-label">{{ $t('portal.wrapped.moviesWatched') }}</p>
          <CountUp class="pt-wrapped-big-number" :value="data.movies_count || 0" :duration="2000" />
        </template>

        <template v-else-if="currentSlide === 2">
          <p class="pt-wrapped-label">{{ $t('portal.wrapped.favoriteGenre') }}</p>
          <h2 class="pt-wrapped-glitch">{{ data.top_genre || '—' }}</h2>
        </template>

        <template v-else-if="currentSlide === 3">
          <p class="pt-wrapped-label">{{ $t('portal.wrapped.totalTime') }}</p>
          <CountUp class="pt-wrapped-big-number" :value="data.total_hours || 0" :duration="2000" />
          <p class="pt-wrapped-sub">{{ $t('portal.wrapped.hours') }}</p>
        </template>

        <template v-else-if="currentSlide === 4">
          <p class="pt-wrapped-label">{{ $t('portal.wrapped.topMovie') }}</p>
          <h2>{{ data.top_movie || '—' }}</h2>
        </template>

        <template v-else-if="currentSlide === 5">
          <p class="pt-wrapped-label">{{ $t('portal.wrapped.level') }}</p>
          <CountUp class="pt-wrapped-big-number" :value="data.level || 1" :duration="1500" />
          <p class="pt-wrapped-sub">
            {{ data.badges_count || 0 }} {{ $t('portal.wrapped.badgesUnlocked') }}
          </p>
        </template>

        <template v-else>
          <h2>{{ $t('portal.wrapped.thanks') }}</h2>
          <button
            class="pt-btn pt-btn--primary"
            @click.stop="$router.push({ name: 'portal-settings' })"
          >
            {{ $t('portal.wrapped.backToProfile') }}
          </button>
        </template>
      </div>
    </transition>

    <div class="pt-wrapped-dots">
      <span
        v-for="i in totalSlides"
        :key="i"
        class="pt-dot"
        :class="{ active: currentSlide === i - 1 }"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useApi } from '@/composables/useApi'
import CountUp from '@/components/portal/CountUp.vue'

const { apiGet } = useApi()
const data = ref({})
const currentSlide = ref(0)
const totalSlides = 7

function nextSlide() {
  if (currentSlide.value < totalSlides - 1) {
    currentSlide.value++
  }
}

onMounted(async () => {
  // Wrapped data would come from a dedicated endpoint
  // For now using profile stats
  const profile = await apiGet('/api/portal/profiles/me').catch(() => null)
  if (profile) {
    data.value = {
      movies_count: profile.xp ? Math.floor(profile.xp / 10) : 0,
      top_genre: 'Action',
      total_hours: profile.xp ? Math.floor(profile.xp / 5) : 0,
      top_movie: '—',
      level: profile.level || 1,
      badges_count: 0,
    }
  }
})
</script>

<style scoped>
.pt-wrapped {
  position: fixed;
  inset: 0;
  z-index: 8000;
  background: linear-gradient(135deg, #0f0a1a 0%, #1a0a2e 50%, #0a1628 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  user-select: none;
}
.pt-wrapped-slide {
  text-align: center;
  padding: 2rem;
  max-width: 600px;
}
.pt-wrapped-title {
  font-size: 3rem;
  font-weight: var(--portal-font-black);
  color: #fff;
  margin-bottom: 0.5rem;
}
.pt-wrapped-label {
  font-size: var(--portal-text-md);
  color: rgb(255, 255, 255, 0.6);
  margin-bottom: 1rem;
  text-transform: uppercase;
  letter-spacing: var(--portal-tracking-eyebrow);
}
.pt-wrapped-big-number {
  font-size: 5rem;
  font-weight: var(--portal-font-black);
  color: var(--accent);
  display: block;
}
.pt-wrapped-sub {
  font-size: var(--portal-text-md);
  color: rgb(255, 255, 255, 0.5);
  margin-top: 0.5rem;
}
.pt-wrapped-glitch {
  font-size: 2.5rem;
  font-weight: var(--portal-font-extrabold);
  color: #fff;
  animation: pt-glitch 0.3s ease-in-out;
}
.pt-wrapped-dots {
  position: absolute;
  bottom: 2rem;
  display: flex;
  gap: 0.5rem;
}
.pt-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--portal-radius-circle);
  background: rgb(255, 255, 255, 0.2);
}
.pt-dot.active {
  background: var(--accent);
}
.pt-btn {
  padding: 0.6rem 2rem;
  border-radius: var(--radius-btn);
  border: none;
  font-weight: var(--portal-font-bold);
  cursor: pointer;
  font-size: var(--portal-text-md);
}
.pt-btn--primary {
  background: var(--accent);
  color: #fff;
}

.pt-slide-enter-active {
  animation: pt-slide-in 0.5s ease;
}
.pt-slide-leave-active {
  animation: pt-slide-out 0.3s ease;
}

@keyframes pt-slide-in {
  from {
    opacity: 0;
    transform: translateY(30px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
@keyframes pt-slide-out {
  from {
    opacity: 1;
  }
  to {
    opacity: 0;
    transform: translateY(-20px);
  }
}
@keyframes pt-glitch {
  0%,
  100% {
    transform: none;
  }
  25% {
    transform: translate(-3px, 2px);
  }
  50% {
    transform: translate(3px, -2px);
  }
  75% {
    transform: translate(-1px, 1px);
  }
}

@media (prefers-reduced-motion: reduce) {
  .pt-slide-enter-active,
  .pt-slide-leave-active,
  .pt-wrapped-glitch {
    animation: none;
  }
}
</style>
