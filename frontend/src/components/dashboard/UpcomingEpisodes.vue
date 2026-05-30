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
          v-for="(ep, i) in displayEpisodes"
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
              <span class="uc-badge-dot" />
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

// Honour the OS "reduce motion" preference: the auto-scroll marquee is
// swapped for a manual horizontal scroller (see the reduced-motion CSS), and
// we render the single episode set instead of the doubled marquee set so
// series are not listed twice when the user scrolls the strip by hand.
const prefersReducedMotion = ref(false)
let _motionQuery = null
function _syncMotionPref(e) {
  prefersReducedMotion.value = e.matches
}

const displayEpisodes = computed(() =>
  prefersReducedMotion.value ? episodes.value : loopedEpisodes.value
)

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
  if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
    _motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    prefersReducedMotion.value = _motionQuery.matches
    if (typeof _motionQuery.addEventListener === 'function') {
      _motionQuery.addEventListener('change', _syncMotionPref)
    } else if (typeof _motionQuery.addListener === 'function') {
      _motionQuery.addListener(_syncMotionPref)
    }
  }
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
  if (_motionQuery) {
    if (typeof _motionQuery.removeEventListener === 'function') {
      _motionQuery.removeEventListener('change', _syncMotionPref)
    } else if (typeof _motionQuery.removeListener === 'function') {
      _motionQuery.removeListener(_syncMotionPref)
    }
    _motionQuery = null
  }
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
  if (diff < 0) {
    const n = Math.abs(diff)
    return `-${t('dashboard.upcomingInDays', { n }, n)}`
  }
  if (diff < 7) return t('dashboard.upcomingInDays', { n: diff }, diff)
  if (diff < 30) {
    const n = Math.ceil(diff / 7)
    return t('dashboard.upcomingInWeeks', { n }, n)
  }
  const n = Math.ceil(diff / 30)
  return t('dashboard.upcomingInMonths', { n }, n)
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
  background: var(--card-bg);
  border-radius: var(--radius-card);
  border: var(--border-width-thin) solid var(--card-border);
  overflow: hidden;
  height: 100%;
  display: flex;
  flex-direction: column;
}
.uc-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3-5) var(--space-4) 0;
  flex-shrink: 0;
}
.uc-title {
  font-size: var(--text-2xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: var(--tracking-widest);
}
.uc-count {
  /* 9 px count chip — matches the kind labels in PortalUpcomingEvents
     for visual rhythm. */
  font-size: 9px;
  background: rgb(var(--color-module-watchlist-rgb), 0.2);
  color: var(--text-primary);
  /* 1 / 6 px chip padding — vertical sub-token, horizontal between
     --space-1 and --space-2. */
  padding: 1px 6px;
  border-radius: var(--radius-btn);
  font-weight: var(--font-medium);
}
.uc-empty {
  padding: var(--space-6) var(--space-4);
  font-size: var(--text-xs);
  color: var(--text-muted);
}

/* Skeleton */
.uc-skel-list {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-3-5) var(--space-4);
  flex: 1;
  min-height: 0;
}
.uc-skel-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.uc-skel-poster {
  width: 100%;
  aspect-ratio: var(--aspect-poster);
  border-radius: var(--radius-btn);
  background: var(--gradient-skeleton-shimmer);
  background-size: 200% 100%;
  animation: uc-shimmer var(--duration-animation) ease-in-out infinite;
}
.uc-skel-line {
  border-radius: var(--radius-sm);
  background: var(--gradient-skeleton-shimmer);
  background-size: 200% 100%;
  animation: uc-shimmer var(--duration-animation) ease-in-out infinite;
}
.uc-skel-line-title {
  height: 12px;
  width: 80%;
}
.uc-skel-line-sub {
  height: 10px;
  width: 50%;
}
@keyframes uc-shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

/* Viewport clips the track, track slides via CSS animation */
.uc-viewport {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  padding: var(--space-3) 0 var(--space-3-5);
  /* 16 px edge fade — hero-only mask outside the spacing scale. */
  -webkit-mask-image: linear-gradient(
    to right,
    transparent,
    black 16px,
    black calc(100% - 16px),
    transparent
  );
  mask-image: linear-gradient(
    to right,
    transparent,
    black 16px,
    black calc(100% - 16px),
    transparent
  );
}

.uc-track {
  display: flex;
  /* Gap mirrors the GAP constant in the script (14 px) — keep both in
     sync since setWidth derives from CARD_W + GAP. */
  gap: var(--space-3-5);
  padding: 0 var(--space-4);
  width: max-content;
  animation: uc-scroll var(--anim-duration, 60s) linear infinite;
}
.uc-track.uc-paused {
  animation-play-state: paused;
}

@keyframes uc-scroll {
  0% {
    transform: translateX(0);
  }
  100% {
    transform: translateX(calc(var(--set-width, 1000px) * -1));
  }
}

.uc-card {
  flex-shrink: 0;
  /* Card width mirrors the CARD_W constant in the script (140 px). */
  width: 140px;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  text-decoration: none;
  color: inherit;
  transition: transform var(--duration-base);
}
.uc-card:hover {
  transform: translateY(-3px);
}

.uc-poster {
  width: 100%;
  aspect-ratio: var(--aspect-poster);
  border-radius: var(--radius-btn);
  background: var(--heat-0, var(--surface-2));
  overflow: hidden;
  position: relative;
}
.uc-poster img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform var(--duration-slow);
}
.uc-card:hover .uc-poster img {
  transform: scale(1.05);
}
.uc-poster-ph {
  /* 24 px placeholder glyph — between --text-lg (~20.8) and
     --text-xl (clamp). Poster-only fallback. */
  font-size: 24px;
  opacity: 0.2;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
}

.uc-badge {
  /* Mirrors the portal poster ``.mk-poster__avail`` pill: pill shape,
     frosted veil background, current-colour border + dot, uppercase
     micro-label. Tints (red / yellow / grey) stay specific to the
     date-proximity colour code. */
  position: absolute;
  /* 6 / 6 px corner inset — too small for --space-2 (8). */
  top: 6px;
  right: 6px;
  display: inline-flex;
  align-items: center;
  /* 3 px dot-to-label gap — between --space-half (2) and --space-1 (4). */
  gap: 3px;
  /* 2 / 6 / 2 / 4 px asymmetric padding — extra left room compensates
     for the inline dot, matches the portal Dispo pill exactly. */
  padding: 2px 6px 2px 4px;
  border-radius: var(--radius-pill);
  background: rgb(var(--bg-primary-rgb), 0.55);
  backdrop-filter: var(--blur-xs);
  -webkit-backdrop-filter: var(--blur-xs);
  font-size: 9px;
  font-weight: var(--font-extrabold);
  letter-spacing: var(--tracking-widest);
  text-transform: uppercase;
  box-shadow: var(--shadow-sm);
  border: var(--border-width) solid transparent;
}
.uc-badge-dot {
  /* 4 px dot — currentColor + subtle glow, mirrors
     ``.mk-poster__avail-dot``. */
  width: 4px;
  height: 4px;
  border-radius: var(--radius-pill);
  background: currentcolor;
  box-shadow: 0 0 4px currentcolor;
}
.badge-past {
  color: var(--text-very-faint);
  border-color: var(--border-default);
}
.badge-imminent {
  color: var(--color-error-light);
  border-color: rgb(var(--color-error-rgb), 0.33);
}
.badge-soon {
  color: var(--color-warning-light);
  border-color: rgb(var(--color-warning-rgb), 0.33);
}
.badge-later {
  color: var(--text-muted);
  border-color: var(--border-default);
}

.uc-meta {
  display: flex;
  flex-direction: column;
  gap: var(--space-half);
  padding: 0 var(--space-half);
}
.uc-series {
  font-size: var(--text-xs);
  font-weight: var(--font-regular);
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.uc-ep {
  font-size: var(--text-3xs);
  color: var(--text-muted);
}
.uc-date {
  font-size: var(--text-3xs);
  color: var(--text-muted);
}

@media (prefers-reduced-motion: reduce) {
  .uc-skel-poster,
  .uc-skel-line {
    animation: none;
  }
  .uc-track {
    /* Stop the auto-scrolling marquee. The viewport below becomes a manual
       horizontal scroller so every upcoming episode stays reachable
       without any auto-motion. */
    animation: none;
  }
  .uc-viewport {
    /* Reduced-motion fallback: no marquee, but the strip must stay fully
       browsable. Turn the clipped viewport into a horizontal scroller and
       drop the edge-fade mask (it would hide the cards near the edges and
       the scroll affordance). */
    overflow: auto hidden;
    scroll-snap-type: x proximity;
    scroll-padding-inline: var(--space-4);
    -webkit-mask-image: none;
    mask-image: none;
  }
  .uc-card {
    scroll-snap-align: start;
  }
  .uc-card,
  .uc-poster img {
    transition: none;
  }
}
</style>
