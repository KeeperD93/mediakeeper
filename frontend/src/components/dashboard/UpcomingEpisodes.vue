<template>
  <div class="uc">
    <div class="uc-header">
      <span class="uc-title">{{ $t('dashboard.upcomingTitle') }}</span>
      <span v-if="episodes.length > 0" class="uc-count">{{ episodes.length }}</span>
    </div>
    <div v-if="loading" class="uc-skel-list">
      <div v-for="n in 3" :key="n" class="uc-skel-card">
        <div class="uc-skel-poster" />
        <div class="uc-skel-line uc-skel-line-title" />
        <div class="uc-skel-line uc-skel-line-sub" />
      </div>
    </div>
    <div v-else-if="episodes.length === 0" class="uc-empty">
      {{ $t('dashboard.noUpcomingEps') }}
    </div>
    <div v-else class="uc-viewport" @mouseenter="paused = true" @mouseleave="paused = false">
      <div class="uc-track" :class="{ 'uc-paused': paused }" :style="trackStyle">
        <a
          v-for="(ep, i) in loopedEpisodes"
          :key="'ep-' + i"
          class="uc-card"
          :href="tmdbUrl(ep)"
          target="_blank"
          rel="noopener"
        >
          <div class="uc-poster">
            <img
              v-if="ep.poster"
              :src="ep.poster"
              :alt="ep.series_name"
              loading="lazy"
              @error="$event => ($event.target.style.display = 'none')"
            />
            <span v-else class="uc-poster-ph">📺</span>
            <span class="uc-badge" :class="dateClass(ep.air_date)">
              {{ relativeDate(ep.air_date) }}
            </span>
          </div>
          <div class="uc-meta">
            <span class="uc-series">{{ ep.series_name }}</span>
            <span class="uc-ep">
              S{{ String(ep.season).padStart(2, '0') }}E{{ String(ep.episode).padStart(2, '0') }}
            </span>
            <span class="uc-date">{{ formatDate(ep.air_date) }}</span>
          </div>
        </a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '@/composables/useApi'

const CARD_W = 140
const GAP = 14

const { apiGet } = useApi()
const { t } = useI18n()
const episodes = ref([])
const loading = ref(true)
const paused = ref(false)
let retryTimer = null

// Duplicate for seamless loop
const loopedEpisodes = computed(() => {
  if (episodes.value.length === 0) return []
  return [...episodes.value, ...episodes.value]
})

// Total width of one set of cards
const setWidth = computed(() => episodes.value.length * (CARD_W + GAP))

// CSS animation duration: slower = more items. ~8s per card width
const animDuration = computed(() => Math.max(20, episodes.value.length * 8))

const trackStyle = computed(() => ({
  '--set-width': setWidth.value + 'px',
  '--anim-duration': animDuration.value + 's',
}))

async function fetchData() {
  try {
    const data = await apiGet('/api/watchlist/upcoming')
    if (Array.isArray(data) && data.length > 0) {
      episodes.value = data
      loading.value = false
      return true
    }
  } catch {
    /* silent: widget fetch, card stays blank */
  }
  return false
}

onMounted(async () => {
  const ok = await fetchData()
  if (!ok) {
    let attempts = 0
    retryTimer = setInterval(async () => {
      attempts++
      const success = await fetchData()
      if (success || attempts >= 6) {
        clearInterval(retryTimer)
        loading.value = false
      }
    }, 5000)
  }
})
onUnmounted(() => {
  if (retryTimer) clearInterval(retryTimer)
})

function tmdbUrl(ep) {
  return ep.tmdb_id ? `https://www.themoviedb.org/tv/${ep.tmdb_id}` : '#'
}
function formatDate(dateStr) {
  if (!dateStr) return '—'
  return new Date(dateStr + 'T00:00:00').toLocaleDateString(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}
function relativeDate(dateStr) {
  if (!dateStr) return ''
  const now = new Date()
  now.setHours(0, 0, 0, 0)
  const diff = Math.round((new Date(dateStr + 'T00:00:00') - now) / 86400000)
  if (diff === 0) return t('common.today')
  if (diff === 1) return t('common.tomorrow')
  if (diff < 0) return `${diff}j`
  if (diff < 7) return `${diff}j`
  if (diff < 30) return `${Math.ceil(diff / 7)} sem.`
  return `${Math.ceil(diff / 30)} mois`
}
function dateClass(dateStr) {
  if (!dateStr) return ''
  const now = new Date()
  now.setHours(0, 0, 0, 0)
  const diff = Math.round((new Date(dateStr + 'T00:00:00') - now) / 86400000)
  if (diff < 0) return 'badge-past'
  if (diff <= 1) return 'badge-imminent'
  if (diff <= 7) return 'badge-soon'
  return 'badge-later'
}
</script>

<style scoped>
.uc {
  background: var(--card-bg, rgb(255,255,255,0.03)); border-radius:var(--radius-card);
  border: 0.5px solid var(--card-border, rgb(255,255,255,0.05));
  overflow: hidden; height: 100%; display: flex; flex-direction: column;
}
.uc-header { display: flex; align-items: center; gap: 8px; padding: 14px 16px 0; flex-shrink: 0; }
.uc-title { font-size: var(--text-2xs); color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.uc-count { font-size: 9px; background: rgb(139,92,246,0.2); color: #a78bfa; padding: 1px 6px; border-radius:var(--radius-btn); font-weight: var(--font-medium); }
.uc-empty { padding: 24px 16px; font-size: var(--text-xs); color: var(--text-muted); }

/* Skeleton */
.uc-skel-list { display: flex; gap: 12px; padding: 14px 16px; flex: 1; min-height: 0; }
.uc-skel-card { flex: 1; display: flex; flex-direction: column; gap: 8px; }
.uc-skel-poster { width: 100%; aspect-ratio: 2/3; border-radius:var(--radius-btn); background: linear-gradient(90deg, rgb(255,255,255,0.02) 25%, var(--surface-3) 50%, rgb(255,255,255,0.02) 75%); background-size: 200% 100%; animation: uc-shimmer var(--duration-animation) ease-in-out infinite; }
.uc-skel-line { border-radius: 4px; background: linear-gradient(90deg, rgb(255,255,255,0.02) 25%, var(--surface-3) 50%, rgb(255,255,255,0.02) 75%); background-size: 200% 100%; animation: uc-shimmer var(--duration-animation) ease-in-out infinite; }
.uc-skel-line-title { height: 12px; width: 80%; }
.uc-skel-line-sub { height: 10px; width: 50%; }
@keyframes uc-shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

/* Viewport clips the track, track slides via CSS animation */
.uc-viewport {
  flex: 1; min-height: 0; overflow: hidden;
  padding: 12px 0 14px;
  /* Fade edges */
  -webkit-mask-image: linear-gradient(to right, transparent, black 16px, black calc(100% - 16px), transparent);
  mask-image: linear-gradient(to right, transparent, black 16px, black calc(100% - 16px), transparent);
}

.uc-track {
  display: flex; gap: 14px;
  padding: 0 16px;
  width: max-content;
  animation: uc-scroll var(--anim-duration, 60s) linear infinite;
}
.uc-track.uc-paused { animation-play-state: paused; }

@keyframes uc-scroll {
  0% { transform: translateX(0); }
  100% { transform: translateX(calc(var(--set-width, 1000px) * -1)); }
}

.uc-card { flex-shrink: 0; width: 140px; display: flex; flex-direction: column; gap: 8px; text-decoration: none; color: inherit; transition: transform var(--duration-base); }
.uc-card:hover { transform: translateY(-3px); }

.uc-poster { width: 100%; aspect-ratio: 2/3; border-radius:var(--radius-btn); background: var(--heat-0, var(--surface-2)); overflow: hidden; position: relative; }
.uc-poster img { width: 100%; height: 100%; object-fit: cover; transition: transform var(--duration-slow); }
.uc-card:hover .uc-poster img { transform: scale(1.05); }
.uc-poster-ph { font-size: 24px; opacity: 0.2; display: flex; align-items: center; justify-content: center; width: 100%; height: 100%; }

.uc-badge { position: absolute; bottom: 6px; left: 6px; font-size: 9px; font-weight: var(--font-medium); padding: 2px 7px; border-radius:var(--radius-sm); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); }
.badge-past { background: var(--surface-3); color: var(--text-very-faint); }
.badge-imminent { background: rgb(var(--color-error-rgb),0.25); color: #fca5a5; }
.badge-soon { background: rgb(250,204,21,0.2); color: #fde68a; }
.badge-later { background: rgb(255,255,255,0.08); color: var(--text-muted); }

.uc-meta { display: flex; flex-direction: column; gap: 2px; padding: 0 2px; }
.uc-series { font-size: var(--text-xs); font-weight: var(--font-regular); color: var(--text-secondary)); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.uc-ep { font-size: var(--text-3xs); color: var(--text-muted); }
.uc-date { font-size: var(--text-3xs); color: var(--text-muted); }
</style>
