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
        <template v-for="(item, i) in displayItems" :key="'it-' + i">
          <span v-if="item.type === 'sep'" class="uc-sep" aria-hidden="true" />
          <a
            v-else
            class="uc-card"
            :class="{ 'uc-card--group': item.count }"
            :href="tmdbUrl(item)"
            target="_blank"
            rel="noopener"
          >
            <div class="uc-poster">
              <img
                v-if="item.poster"
                :src="item.poster"
                :alt="item.series_name"
                loading="lazy"
                @error="$event => ($event.target.style.display = 'none')"
              />
              <span v-else class="uc-poster-ph">📺</span>
              <span class="uc-badge" :class="dateClass(item.air_date)">
                <span class="uc-badge-dot" />
                {{ relativeDate(item.air_date) }}
              </span>
              <span v-if="item.count" class="uc-count-badge">
                <Layers :size="9" />
                {{ item.count }}
              </span>
            </div>
            <div class="uc-meta">
              <span class="uc-series">{{ item.series_name }}</span>
              <span class="uc-ep">{{ epLabel(item) }}</span>
              <span class="uc-date">{{ formatDate(item.air_date) }}</span>
            </div>
          </a>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Layers } from 'lucide-vue-next'
import { useApi } from '@/composables/useApi'
import { tmdbWebUrl } from '@/utils/tmdb'
import { localizedDate } from '@/utils/datetime'

import '@/assets/styles/dashboard/upcoming-episodes.css'

const CARD_W = 140
const GAP = 14
const SEP_W = 3

const { apiGet } = useApi()
const { t, locale } = useI18n()
const episodes = ref([])
const loading = ref(true)
const paused = ref(false)
let retryTimer = null

const pad = n => String(n ?? 0).padStart(2, '0')

// Collapse episodes of the same series + season landing on the same day into a
// single card ("Saison X — N épisodes"); a lone episode keeps its own card.
const groupedItems = computed(() => {
  const groups = new Map()
  for (const ep of episodes.value) {
    const key = `${ep.tmdb_id}|${ep.air_date}|${ep.season}`
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key).push(ep)
  }
  const out = []
  const seen = new Set()
  for (const ep of episodes.value) {
    const key = `${ep.tmdb_id}|${ep.air_date}|${ep.season}`
    if (seen.has(key)) continue
    seen.add(key)
    const grp = groups.get(key)
    out.push(grp.length >= 2 ? { ...grp[0], count: grp.length } : { ...grp[0] })
  }
  return out
})

// Honour the OS "reduce motion" preference: the auto-scroll marquee is
// swapped for a manual horizontal scroller (see the reduced-motion CSS), and
// we render a single set so series are not listed twice when scrolled by hand.
const prefersReducedMotion = ref(false)
let _motionQuery = null
function _syncMotionPref(e) {
  prefersReducedMotion.value = e.matches
}

// Marquee duplicates the set; a thin separator marks the loop seam (last →
// first). Reduced motion shows one set with a trailing seam marker.
const displayItems = computed(() => {
  const cards = groupedItems.value.map(c => ({ ...c, type: 'card' }))
  if (cards.length === 0) return []
  const sep = { type: 'sep' }
  return prefersReducedMotion.value ? [...cards, sep] : [...cards, sep, ...cards, sep]
})

// Width of one looped unit: the grouped cards + one separator + their gaps.
const setWidth = computed(() => {
  const n = groupedItems.value.length
  return n * CARD_W + SEP_W + (n + 1) * GAP
})

// CSS animation duration: slower = more items. ~8s per card width
const animDuration = computed(() => Math.max(20, groupedItems.value.length * 8))

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

// Re-fetch when the UI language changes so titles + posters come back
// localized (the backend resolves them per the viewer's X-MK-Locale header).
watch(locale, () => {
  loading.value = true
  episodes.value = []
  fetchData()
})

function tmdbUrl(ep) {
  return ep.tmdb_id ? tmdbWebUrl('tv', ep.tmdb_id, locale.value) : '#'
}
function epLabel(item) {
  if (item.count) {
    return t(
      'dashboard.upcomingEpCount',
      { season: pad(item.season), count: item.count },
      item.count,
    )
  }
  return t('dashboard.upcomingEpLabel', { season: pad(item.season), episode: pad(item.episode) })
}
function formatDate(dateStr) {
  if (!dateStr) return '—'
  return localizedDate(new Date(dateStr + 'T00:00:00'), {
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
